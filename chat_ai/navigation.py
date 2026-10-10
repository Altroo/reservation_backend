"""Only existing native routes; apartments/rents resolve through their parent."""
from chat_ai_assistant.contracts import ChatAIError
ROUTES={'dashboard':'','reservations':'reservations','buildings':'buildings','costs':'costs','calendar':'calendar','planning':'planning','occupancy':'occupancy','balance':'balance','gains':'gains','locals':'locaux','local_planning':'locaux/planning','local_dashboard':'locaux/dashboard','hilton_reports':'hilton-reports','hilton_settings':'settings/hilton-report','users':'users'}
DETAILS={'reservation':'reservations','building':'buildings','cost':'costs','local':'locaux','user':'users'}
EDIT_FORMS=set(DETAILS)
FORM_NEW=set(DETAILS)
LIST_RESOURCE={'reservations':'reservation','buildings':'building','costs':'cost','calendar':'reservation','planning':'reservation','occupancy':'reservation','balance':'reservation','gains':'reservation','dashboard':'reservation','locals':'local','local_planning':'local','local_dashboard':'local','hilton_reports':'hilton_report','users':'user','hilton_settings':'user'}

class ChatAINavigationResolver:
    @staticmethod
    def resolve(resource, scope_id=1, identifier=None):
        if type(scope_id) is not int or scope_id!=1:raise ChatAIError('INVALID_ARGUMENTS')
        base,suffix=resource,''
        if resource.endswith('_edit'):
            base,suffix=resource[:-5],'/edit'
            if base not in EDIT_FORMS:raise ChatAIError('INVALID_ARGUMENTS')
        if resource.endswith('_new'):
            base=resource[:-4]
            if base not in FORM_NEW or identifier is not None:raise ChatAIError('INVALID_ARGUMENTS')
            path='/dashboard/'+DETAILS[base]+'/new'
        elif base in DETAILS and type(identifier) is int and 0<identifier<=2147483647:
            path='/dashboard/'+DETAILS[base]+'/'+str(identifier)+suffix
        elif resource in ROUTES and identifier is None:path='/dashboard/'+ROUTES[resource]
        else:raise ChatAIError('INVALID_ARGUMENTS')
        return {'application':'reservation','resource':resource,'identifier':identifier,'path':path}
