"""Bounded tools backed by native filters, calculations and current permissions."""
from datetime import date, timedelta
from types import SimpleNamespace
import time
from django.conf import settings
from django.db import connection, transaction, OperationalError
from django.db.models import Q
from django.http import QueryDict
from django.utils import timezone
from chat_ai_assistant.contracts import ChatAIError, ChatAITool, ChatAIToolRegistry, object_schema, ID, STRING
from reservation.filters import ReservationFilter
from local.filters import LocalFilter, LoyerFilter
from .security import authorize, capabilities, authorize_resource
from .resources import RESOURCES
from .models import AuditEvent
from .navigation import ChatAINavigationResolver, ROUTES, DETAILS, EDIT_FORMS, FORM_NEW, LIST_RESOURCE
from .knowledge import ChatAIKnowledgeService
from .labels import FIELD_LABELS, FIELD_LABELS_EN

RESOURCE={'type':'string','enum':list(RESOURCES)}
DATE={'type':'string','pattern':r'^\d{4}-\d{2}-\d{2}$'}
YEAR={'type':'integer','minimum':1970,'maximum':2099}
METRICS={
 'reservation_amount':('Montants des réservations','Reservation amounts','Montants attribués à l’année d’arrivée ; ne signifie pas encaissements.','Amounts assigned to the arrival year; not collected payments.'),
 'reservation_costs':('Coûts enregistrés','Recorded costs','Coûts datés de l’année sélectionnée.','Costs dated in the selected year.'),
 'reservation_balance':('Solde réservations moins coûts','Reservation amounts minus costs','Montants des réservations à l’arrivée moins coûts enregistrés ; indicateur du tableau de bord.','Arrival-year reservation amounts minus recorded costs; a dashboard metric.'),
 'returned_amount':('Montants retournés Airbnb et Bank','Returned Airbnb and Bank amounts','Uniquement les sources Airbnb et Bank, année d’arrivée, marquées retournées.','Only Airbnb and Bank sources, arrival year, marked returned.'),
 'unreturned_amount':('Montants non retournés Airbnb et Bank','Unreturned Airbnb and Bank amounts','Uniquement les sources Airbnb et Bank, année d’arrivée, non retournées.','Only Airbnb and Bank sources, arrival year, not marked returned.'),
 'paid_rent':('Loyers payés','Paid rents','Loyers enregistrés et marqués payés pour l’année de location ; pas un bénéfice comptable.','Recorded rents marked paid for the rental year; not accounting profit.'),
}


def registry():
    search=object_schema({'resource':RESOURCE,'query':STRING,'building_name':STRING,'apartment_name':STRING,'guest_name':STRING,'local_name':STRING,'payment_source':STRING,'date_from':DATE,'date_to':DATE,'year':YEAR,'month':{'type':'integer','minimum':1,'maximum':12},'paid':{'type':'boolean'},'rented':{'type':'boolean'},'returned':{'type':'boolean'},'limit':{'type':'integer','minimum':1,'maximum':10},'offset':{'type':'integer','minimum':0,'maximum':100}},['resource'])
    writable=[name for name,spec in RESOURCES.items() if spec.editable]
    specs=[
      ('search_records','Find authorized reservations, residences, apartments, costs, premises, recorded rents, saved Hilton reports or staff users by description. Filters combine with AND. Rent results exclude implicit unrecorded dues.',search,('read',)),
      ('get_record','Read a known internal identifier or the current page after fresh authorization.',object_schema({'resource':RESOURCE,'identifier':ID},['resource']),('read',)),
      ('navigate','Open an existing permitted list, record or native form. Apartments open their residence and rents their premises; saved Hilton reports use the reports screen.',object_schema({'resource':{'type':'string','enum':list(ROUTES)+list(RESOURCES)+[x+'_edit' for x in sorted(EDIT_FORMS)]+[x+'_new' for x in sorted(FORM_NEW)]},'identifier':ID},['resource']),('read',)),
      ('financial_summary','Read one native ANNUAL metric for a specified year, optionally a known residence. Reservation amounts, returned Airbnb/Bank amounts and paid rents are distinct. No monthly or arbitrary-date metric here.',object_schema({'metric':{'type':'string','enum':list(METRICS)},'year':YEAR,'building_id':ID},['metric','year']),('read','financial')),
      ('knowledge','Retrieve verified permission-filtered application procedures.',object_schema({'query':STRING},['query']),('read',)),
      ('previous_results','List saved authorized results or open one by its one-based index.',object_schema({'operation':{'type':'string','enum':['open','list']},'index':{'type':'integer','minimum':1,'maximum':10}},['operation']),('read',)),
      ('prepare_change','Propose an exact known record edit/delete for separate confirmation using native permissions. Only listed prose fields. No amounts, dates, relationships, payment flags, Hilton report writes or user/permission changes.',object_schema({'resource':{'type':'string','enum':writable},'identifier':ID,'operation':{'type':'string','enum':['update','delete']},'changes':{'type':'object','maxProperties':8,'propertyNames':{'enum':sorted({f for s in RESOURCES.values() for f in s.editable})},'additionalProperties':{'type':['string','null'],'maxLength':1000}}},['resource','identifier','operation']),('read',)),
    ]
    return ChatAIToolRegistry([ChatAITool(name,description,schema,{'type':'object'},name,application='reservation',required_capabilities=caps,authorization='fresh native user flags, separate Hilton access and staff-only user access',classification='proposal' if name=='prepare_change' else 'read',audit_classification='business_proposal' if name=='prepare_change' else 'business_read') for name,description,schema,caps in specs])


def native_request(user, **filters):
    params=QueryDict('',mutable=True)
    for key,value in filters.items():
        if value not in ('',None):params[key]=str(value).lower() if type(value) is bool else str(value)
    return SimpleNamespace(user=user,query_params=params,GET=params,data={},method='GET')


class ChatAIToolExecutor:
    def __init__(self,user_id,scope_id,request_id,state=None,context=None,audit=True,instruction=None):
        self.user_id,self.scope_id,self.request_id=user_id,scope_id,request_id
        self.state,self.context=state or {},context or {}
        self.audit,self.instruction=audit,instruction

    def authorize(self):return authorize(self.user_id,self.scope_id)
    authorize_context=authorize
    def capabilities(self):return capabilities(self.authorize())
    def output_labels(self):return FIELD_LABELS_EN if self.context.get('interface_language')=='en' else FIELD_LABELS

    def authorize_knowledge(self,documents):
        sources=[{'document_id':d['document_id'],'version':d['version']} for d in documents]
        if not ChatAIKnowledgeService.sources_authorized(sources,self.scope_id,self.capabilities()):raise ChatAIError('CONTEXT_EXPIRED')

    def execute(self,name,arguments):
        started,outcome=time.monotonic(),'denied'
        try:
            self.authorize();tool=registry().validate(name,arguments)
            if not set(tool.required_capabilities)<=self.capabilities():raise ChatAIError('PERMISSION_DENIED')
            try:
                with transaction.atomic():
                    if connection.vendor=='postgresql':
                        with connection.cursor() as cursor:cursor.execute('SET LOCAL statement_timeout = %s',[tool.timeout_seconds*1000])
                    result=getattr(self,name)(**arguments)
                    if time.monotonic()-started>tool.timeout_seconds:raise ChatAIError('TOOL_TIMEOUT')
                    self.authorize()
            except OperationalError as exc:
                if getattr(exc.__cause__,'pgcode',None) in ('57014','55P03'):raise ChatAIError('TOOL_TIMEOUT') from None
                raise
            outcome='allowed';return result
        finally:
            if self.audit:AuditEvent.objects.create(user_id=self.user_id,actor_id=self.user_id,scope_id=self.scope_id,application='reservation',tool=name[:64],outcome=outcome,correlation_id=self.request_id,model_version=settings.CHAT_AI_MODEL_ID,duration_ms=max(0,int((time.monotonic()-started)*1000)))

    def queryset(self,resource):
        user=self.authorize()
        if resource not in RESOURCES:raise ChatAIError('INVALID_ARGUMENTS')
        authorize_resource(user,self.scope_id,resource)
        qs=RESOURCES[resource].model.objects.all()
        relations={'reservation':('apartment__building',),'apartment':('building',),'cost':('building',),'local':('building',),'rent':('local__building',)}
        return qs.select_related(*relations[resource]) if resource in relations else qs

    def record(self,resource,identifier):
        if type(identifier) is not int or not 0<identifier<=2147483647:raise ChatAIError('INVALID_ARGUMENTS')
        obj=self.queryset(resource).filter(pk=identifier).first()
        if obj is None:raise ChatAIError('NOT_FOUND')
        return obj

    def serialize(self,resource,obj):
        en=self.context.get('interface_language')=='en'
        def detail(fr,english,value):return {'label':fr,'label_en':english,'value':str(value)}
        item={'id':obj.pk,'details':[]}
        if resource=='reservation':
            item.update(name=obj.guest_name[:200],amount=str(obj.amount),currency='MAD',date=obj.check_in.isoformat())
            item['details']=[detail('Appartement','Apartment',obj.apartment.nom),detail('Arrivée','Arrival',obj.check_in),detail('Départ','Departure',obj.check_out),detail('Nuits','Nights',obj.nights),detail('Source de paiement','Payment source',obj.payment_source),detail('Montant retourné','Amount returned',('Yes' if en else 'Oui') if obj.amount_returned else ('No' if en else 'Non'))]
            if obj.apartment.building:item['details'].append(detail('Résidence','Residence',obj.apartment.building.nom))
            item['description']=(obj.notes or '')[:500]
        elif resource=='building':item.update(name=obj.nom[:200])
        elif resource=='apartment':
            item.update(name=obj.nom[:100])
            if obj.building:item['details']=[detail('Résidence','Residence',obj.building.nom)]
        elif resource=='cost':
            item.update(name=obj.description[:300],amount=str(obj.amount),currency='MAD',date=obj.date.isoformat())
            item['details']=[detail('Catégorie','Category',obj.category)]
            if obj.building:item['details'].append(detail('Résidence','Residence',obj.building.nom))
        elif resource=='local':
            item.update(name=obj.nom[:200],description=obj.adresse[:500])
            item['details']=[detail('Locataire','Tenant',obj.locataire_nom),detail('En location','Rented',('Yes' if en else 'Oui') if obj.en_location else ('No' if en else 'Non')),detail('Loyer mensuel HT','Monthly rent excluding tax',str(obj.prix_location_mensuel)+' MAD')]
            if obj.building:item['details'].append(detail('Résidence','Residence',obj.building.nom))
        elif resource=='rent':
            item.update(name=obj.local.nom[:200]+' · '+f'{obj.mois:02d}/{obj.annee}',amount=str(obj.montant),currency='MAD',status='paid' if obj.paye else 'unpaid')
            item['details']=[detail('Type de résultat','Result type','Recorded rent' if en else 'Loyer enregistré')]
            if obj.date_paiement:item['details'].append(detail('Date de paiement','Payment date',obj.date_paiement))
            item['description']=(obj.notes or '')[:500]
        elif resource=='hilton_report':
            item.update(name=('Hilton report' if en else 'Rapport Hilton')+' · '+obj.start_date.isoformat()+' / '+obj.end_date.isoformat(),amount=str(obj.net_total),currency='MAD')
            item['details']=[detail('Solde net enregistré','Saved net balance',str(obj.net_total)+' MAD'),detail('Balance à reporter','Opening balance',str(obj.opening_balance)+' MAD'),detail('Revenu brut','Gross revenue',str(obj.gross_revenue)+' MAD')]
            item['description']=(obj.notes or '')[:500]
        elif resource=='user':item.update(name=(obj.first_name+' '+obj.last_name).strip() or obj.email,description=obj.email)
        caps=self.capabilities();spec=RESOURCES[resource]
        item['can_update']=bool(spec.editable and 'update' in caps)
        item['can_delete']=bool(spec.deletable and 'delete' in caps)
        target_resource,target_id=resource,obj.pk
        if resource=='apartment':target_resource,target_id='building',obj.building_id
        elif resource=='rent':target_resource,target_id='local',obj.local_id
        elif resource=='hilton_report':target_resource,target_id='hilton_reports',None
        item['navigation']=ChatAINavigationResolver.resolve(target_resource,self.scope_id,target_id) if target_id or target_resource=='hilton_reports' else None
        if resource=='hilton_report':item['open_label']='Open reports' if en else 'Ouvrir les rapports'
        return item

    def read_records(self,resource,ids):
        if not isinstance(ids,list) or len(ids)>10:raise ChatAIError('INVALID_ARGUMENTS')
        result=[]
        for identifier in ids:
            try:result.append(self.serialize(resource,self.record(resource,identifier)))
            except ChatAIError as exc:
                if exc.code!='NOT_FOUND':raise
        return result

    def search_records(self,resource,query='',limit=5,offset=0,**filters):
        qs=self.queryset(resource)
        permitted={
         'reservation':{'building_name','apartment_name','guest_name','payment_source','date_from','date_to','year','month','returned'},
         'building':set(),'apartment':{'building_name'},'cost':{'building_name','date_from','date_to','year','month'},
         'local':{'building_name','rented'},'rent':{'building_name','local_name','year','month','paid'},
         'hilton_report':{'date_from','date_to'},'user':set(),
        }
        if set(filters)-permitted[resource]:raise ChatAIError('INVALID_ARGUMENTS')
        try:
            start=date.fromisoformat(filters['date_from']) if 'date_from' in filters else None
            end=date.fromisoformat(filters['date_to']) if 'date_to' in filters else None
            if start and end and end<start:raise ValueError
        except (TypeError,ValueError):raise ChatAIError('INVALID_ARGUMENTS') from None
        if resource=='reservation':
            mapping={'guest_name':'guest_name','payment_source':'payment_source','date_from':'check_in_after','date_to':'check_in_before','year':'year','month':'month'}
            params={mapping[k]:v for k,v in filters.items() if k in mapping}
            if query:params['search']=query
            f=ReservationFilter(params,queryset=qs)
            if not f.is_valid():raise ChatAIError('INVALID_ARGUMENTS')
            qs=f.qs
            if filters.get('apartment_name'):qs=qs.filter(apartment__nom__icontains=filters['apartment_name'])
            if 'returned' in filters:qs=qs.filter(amount_returned=filters['returned'])
        elif resource=='local':
            params={'search':query}
            if 'rented' in filters:params['en_location']=filters['rented']
            f=LocalFilter(params,queryset=qs)
            if not f.is_valid():raise ChatAIError('INVALID_ARGUMENTS')
            qs=f.qs
        elif resource=='rent':
            mapping={'year':'annee','month':'mois','paid':'paye'};f=LoyerFilter({mapping[k]:v for k,v in filters.items() if k in mapping},queryset=qs)
            if not f.is_valid():raise ChatAIError('INVALID_ARGUMENTS')
            qs=f.qs
            if query:qs=qs.filter(Q(local__nom__icontains=query)|Q(local__locataire_nom__icontains=query))
            if filters.get('local_name'):qs=qs.filter(local__nom__icontains=filters['local_name'])
        else:
            if query:
                fields={'building':['nom'],'apartment':['nom'],'cost':['description'],'hilton_report':['notes'],'user':['first_name','last_name','email']}[resource]
                match=Q()
                for field in fields:match|=Q(**{field+'__icontains':query})
                qs=qs.filter(match)
            if resource=='cost':
                for key,lookup in [('date_from','date__gte'),('date_to','date__lte'),('year','date__year'),('month','date__month')]:
                    if key in filters:qs=qs.filter(**{lookup:filters[key]})
            if resource=='hilton_report':
                if start:qs=qs.filter(start_date__gte=start)
                if end:qs=qs.filter(end_date__lte=end)
        if filters.get('building_name'):
            prefix={'reservation':'apartment__building','rent':'local__building'}.get(resource,'building')
            qs=qs.filter(**{prefix+'__nom__icontains':filters['building_name']})
        total=qs.count();items=[self.serialize(resource,obj) for obj in qs.order_by('-pk')[offset:offset+limit]]
        self.state.update(resource=resource,ids=[item['id'] for item in items],expires_at=(timezone.now()+timedelta(minutes=15)).isoformat())
        return {'type':'record_list','language':self.context.get('interface_language','fr'),'resource':resource,'count':total,'items':items,'limit':limit,'offset':offset,'has_more':offset+len(items)<total}

    def get_record(self,resource,identifier=None):
        identifier=identifier or (self.context.get('identifier') if self.context.get('resource')==resource else None)
        obj=self.record(resource,identifier);self.state.update(resource=resource,ids=[obj.pk],expires_at=(timezone.now()+timedelta(minutes=15)).isoformat())
        return {'type':'record_list','language':self.context.get('interface_language','fr'),'resource':resource,'count':1,'items':[self.serialize(resource,obj)]}

    def navigate(self,resource,identifier=None):
        caps=self.capabilities();base=resource.removesuffix('_new').removesuffix('_edit');mapped=LIST_RESOURCE.get(base,base)
        if mapped not in RESOURCES:raise ChatAIError('INVALID_ARGUMENTS')
        authorize_resource(self.authorize(),self.scope_id,mapped)
        if resource.endswith('_new') and 'create' not in caps:raise ChatAIError('PERMISSION_DENIED')
        if resource.endswith('_edit') and 'update' not in caps:raise ChatAIError('PERMISSION_DENIED')
        if base in RESOURCES and not resource.endswith('_new'):
            obj=self.record(base,identifier)
            if resource==base:
                target=self.serialize(base,obj)['navigation']
                if not target:raise ChatAIError('NOT_FOUND')
                return {'type':'navigation','target':target}
        return {'type':'navigation','target':ChatAINavigationResolver.resolve(resource,self.scope_id,identifier)}

    def financial_summary(self,metric,year,building_id=None):
        if 'financial' not in self.capabilities():raise ChatAIError('PERMISSION_DENIED')
        if building_id is not None:self.record('building',building_id)
        from reservation.views import DashboardStatsView, BalanceView
        from local.views import LocalDashboardView
        if metric in ('reservation_amount','reservation_costs','reservation_balance'):
            response=DashboardStatsView.get(native_request(self.authorize(),year=year,building=building_id));key={'reservation_amount':'total_revenue','reservation_costs':'annual_costs','reservation_balance':'net_profit'}[metric]
        elif metric in ('returned_amount','unreturned_amount'):
            response=BalanceView.get(native_request(self.authorize(),year=year,building=building_id));key='total_returned' if metric=='returned_amount' else 'total_not_returned'
        else:response=LocalDashboardView.get(native_request(self.authorize(),year=year,building=building_id));key='total_benefice_ht'
        if response.status_code!=200:raise ChatAIError('APPLICATION_UNAVAILABLE')
        fr,en,definition,definition_en=METRICS[metric]
        return {'type':'financial_summary','metric':metric,'label':fr,'label_en':en,'value':str(response.data[key]),'currency':'MAD','period':{'date_from':f'{year}-01-01','date_to':f'{year}-12-31'},'definition':definition,'definition_en':definition_en}

    def knowledge(self,query):
        docs=ChatAIKnowledgeService().retrieve(query,self.scope_id,self.capabilities());self.authorize_knowledge(docs) if docs else None
        return {'type':'knowledge','documents':docs}

    def previous_results(self,operation,index=None):
        if self.state.get('expires_at','')<=timezone.now().isoformat() or not self.state.get('ids'):raise ChatAIError('CONTEXT_EXPIRED')
        resource=self.state['resource'];ids=self.state['ids']
        if operation=='open':
            if index is None or index>len(ids):raise ChatAIError('INVALID_ARGUMENTS')
            return self.navigate(resource,ids[index-1])
        if index is not None:raise ChatAIError('INVALID_ARGUMENTS')
        return {'type':'record_list','language':self.context.get('interface_language','fr'),'resource':resource,'items':self.read_records(resource,ids)}

    def prepare_change(self,resource,identifier,operation,changes=None):
        from .actions import prepare
        return prepare(self,resource,identifier,operation,changes or {})
