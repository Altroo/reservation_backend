"""Native writes require an owned, unexpired, exact-target confirmation and fresh locks."""
from contextlib import contextmanager
from datetime import timedelta
import hashlib
import json
from django.conf import settings
from django.db import transaction, connection, OperationalError
from django.db.models.deletion import ProtectedError, RestrictedError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import FieldFile
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from simple_history.models import HistoricalRecords
from account.models import CustomUser
from chat_ai_assistant.contracts import ChatAIError
from .models import PendingAction, AuditEvent
from .resources import RESOURCES
from .security import authorize, authorize_change, validate_text
from .labels import FIELD_LABELS, FIELD_LABELS_EN


def fingerprint(obj):
    values={field.attname:getattr(obj,field.attname) for field in obj._meta.concrete_fields}
    values={key:(value.name if isinstance(value,FieldFile) else value) for key,value in values.items()}
    return hashlib.sha256(json.dumps(values,sort_keys=True,cls=DjangoJSONEncoder).encode()).hexdigest()


def native_context(user, scope_id):
    from .tools import native_request
    return {'request':native_request(user)}


def validated_update(resource,obj,changes,user,scope_id):
    spec=RESOURCES[resource]
    if not changes or set(changes)-set(spec.editable):raise ChatAIError('INVALID_ARGUMENTS')
    for value in changes.values():
        if value is not None:
            if not isinstance(value,str) or len(value)>1000:raise ChatAIError('INVALID_ARGUMENTS')
            if value.strip():validate_text(value)
    # Native views accept PUT, not PATCH. Rehydrate only native writable fields
    # from the locked current object; the model controls only allowlisted prose.
    current=spec.serializer(obj,context=native_context(user,scope_id))
    payload={name:current.data[name] for name,field in current.fields.items() if not field.read_only and name in current.data}
    payload.update(changes)
    check=spec.serializer(obj,data=payload,context=native_context(user,scope_id))
    if not check.is_valid():raise ChatAIError('INVALID_ARGUMENTS')
    for name,value in check.validated_data.items():
        if name not in changes and value != getattr(obj,name):
            # A full PUT must not normalize or change an unrequested field.
            raise ChatAIError('ACTION_REJECTED')
    payload.update({name:check.validated_data[name] for name in changes})
    return payload


def ensure_delete_scope(resource,obj):
    if not RESOURCES[resource].deletable:raise ChatAIError('ACTION_REJECTED')
    if resource in ('building','apartment','local'):
        for relation in obj._meta.related_objects:
            if relation.one_to_many and relation.related_model.objects.filter(**{relation.field.name:obj}).exists():
                raise ChatAIError('ACTION_REJECTED')


def checked_object(executor,resource,identifier,operation,changes):
    if resource not in RESOURCES or not RESOURCES[resource].editable:raise ChatAIError('INVALID_ARGUMENTS')
    obj=executor.record(resource,identifier)
    user=executor.authorize();scope_id=executor.scope_id
    authorize_change(user,scope_id,resource,operation)
    if operation=='delete':
        if changes:raise ChatAIError('INVALID_ARGUMENTS')
        ensure_delete_scope(resource,obj)
    elif operation=='update':validated_update(resource,obj,changes,user,scope_id)
    else:raise ChatAIError('INVALID_ARGUMENTS')
    return obj


def confirmation_card(action,obj,language='fr'):
    en=language=='en'
    return {'type':'confirmation','action_id':str(action.pk),'resource':action.resource,'record_id':action.record_id,'operation':action.operation,'label':str(obj)[:300],'changes':action.changes,'before':{key:str(getattr(obj,key)) if getattr(obj,key)is not None else None for key in action.changes},'warning':'This action will be recorded under your identity.' if en else 'Cette action sera enregistrée sous votre identité.'}


def prepare(executor,resource,identifier,operation,changes):
    from .targets import trusted_target
    if not trusted_target(resource,identifier,instruction=executor.instruction or '',context=executor.context,state=executor.state,now=timezone.now()):raise ChatAIError('CONTEXT_EXPIRED')
    obj=checked_object(executor,resource,identifier,operation,changes)
    if operation=='update':
        payload=validated_update(resource,obj,changes,executor.authorize(),executor.scope_id)
        changes={name:payload[name] for name in changes}
    if PendingAction.objects.filter(user_id=executor.user_id,consumed_at__isnull=True,expires_at__gt=timezone.now()).count()>=20:raise ChatAIError('CONTEXT_LIMIT')
    action=PendingAction.objects.create(user_id=executor.user_id,scope_id=executor.scope_id,resource=resource,record_id=obj.pk,operation=operation,changes=changes,fingerprint=fingerprint(obj),expires_at=timezone.now()+timedelta(minutes=5),instruction_id=executor.request_id)
    return confirmation_card(action,obj,executor.context.get('interface_language','fr'))


def replay_confirmation(executor,action):
    en=action.get('language')=='en'
    done='Action already performed under your identity.' if en else 'Action déjà effectuée sous votre identité.'
    pending=PendingAction.objects.filter(pk=action['confirmation_id'],user_id=executor.user_id,scope_id=executor.scope_id).first()
    if pending is None:
        exists=AuditEvent.objects.filter(correlation_id=action['confirmation_id'],actor_id=executor.user_id,scope_id=executor.scope_id,application='reservation',tool__startswith='confirmed_',outcome='allowed').exists()
        return {'type':'confirmation_status','message':done if exists else ('Action unavailable.' if en else 'Action indisponible.')}
    if pending.consumed_at:return {'type':'confirmation_status','message':done}
    if pending.expires_at<=timezone.now():return {'type':'confirmation_status','message':'This confirmation has expired.' if en else 'Cette confirmation a expiré.'}
    obj=checked_object(executor,pending.resource,pending.record_id,pending.operation,pending.changes)
    if fingerprint(obj)!=pending.fingerprint:raise ChatAIError('CONTEXT_EXPIRED')
    return confirmation_card(pending,obj,'en' if en else 'fr')


@contextmanager
def native_history_request(request):
    missing=object();previous=getattr(HistoricalRecords.context,'request',missing)
    HistoricalRecords.context.request=request
    try:yield
    finally:
        if previous is missing:del HistoricalRecords.context.request
        else:HistoricalRecords.context.request=previous


def lock_authorization(user_id,scope_id):
    if not CustomUser.objects.select_for_update().filter(pk=user_id).exists():raise ChatAIError('NOT_AUTHENTICATED')


def confirm(request,id):
    from .tools import ChatAIToolExecutor
    with transaction.atomic():
        if connection.vendor=='postgresql':
            with connection.cursor() as cursor:
                cursor.execute('SET LOCAL lock_timeout = %s',[5000]);cursor.execute('SET LOCAL statement_timeout = %s',[5000])
        action=PendingAction.objects.select_for_update().filter(pk=id,user=request.user).first()
        if action is None:raise ChatAIError('NOT_FOUND')
        user=authorize(request.user.pk,action.scope_id)
        if action.consumed_at or action.expires_at<=timezone.now():raise ChatAIError('CONTEXT_EXPIRED')
        spec=RESOURCES[action.resource]
        # Lock the target before dependency validation; FK insertion must wait.
        obj=spec.model.objects.select_for_update().filter(pk=action.record_id).first()
        if obj is None:raise ChatAIError('CONTEXT_EXPIRED')
        lock_authorization(user.pk,action.scope_id)
        scope_id=action.scope_id
        user=authorize(user.pk,action.scope_id)
        executor=ChatAIToolExecutor(user.pk,action.scope_id,action.pk,audit=False)
        obj=checked_object(executor,action.resource,obj.pk,action.operation,action.changes)
        if action.expires_at<=timezone.now() or fingerprint(obj)!=action.fingerprint:raise ChatAIError('CONTEXT_EXPIRED')
        data=validated_update(action.resource,obj,action.changes,user,scope_id) if action.operation=='update' else None
        factory=APIRequestFactory();path='/'
        native_request=factory.put(path,data,format='json') if data is not None else factory.delete(path)
        force_authenticate(native_request,user=user)
        with native_history_request(request):
            try:response=spec.view.as_view()(native_request,pk=obj.pk)
            except (ProtectedError,RestrictedError):raise ChatAIError('ACTION_REJECTED') from None
        if response.status_code>=400:raise ChatAIError('ACTION_REJECTED')
        action.consumed_at=timezone.now();action.save(update_fields=['consumed_at'])
        AuditEvent.objects.create(user=user,actor_id=user.pk,actor_label=str(user)[:254],application='reservation',scope_id=action.scope_id,resource=action.resource,record_id=action.record_id,changed_fields=sorted(action.changes),tool='confirmed_'+action.operation,outcome='allowed',instruction_id=action.instruction_id,correlation_id=action.pk,model_version=settings.CHAT_AI_MODEL_ID)
    return {'success':True,'operation':action.operation,'resource':action.resource,'record_id':action.record_id}
