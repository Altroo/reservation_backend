"""Reuse native flags; Hilton access is independent of ordinary read access."""
import hashlib
import json
import re
from django.conf import settings
from account.models import CustomUser
from core.permissions import can_view, can_create, can_update, can_delete, can_access_hilton_reports
from chat_ai_assistant.contracts import ChatAIError

APPLICATION_SCOPE = 1  # Internal application partition, never a company or browser authority.
COMMON_RESOURCES = {'reservation', 'building', 'apartment', 'cost', 'local', 'rent'}
SECRET = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:Bearer\s+)[A-Za-z0-9._-]{16,}|(?:password|api[_-]?key|secret|access[_-]?token)\s*[:=]\s*\S+", re.I)


def validate_text(text):
    if not isinstance(text,str) or not text.strip() or len(text)>4000 or '\x00' in text:
        raise ChatAIError('INVALID_ARGUMENTS')
    if SECRET.search(text):raise ChatAIError('SENSITIVE_INPUT')
    return text.strip()


def authorize(user_id, scope_id=APPLICATION_SCOPE):
    if not settings.CHAT_AI_ASSISTANT_ENABLED:raise ChatAIError('APPLICATION_UNAVAILABLE')
    user=CustomUser.objects.filter(pk=user_id,is_active=True).first()
    if user is None:raise ChatAIError('NOT_AUTHENTICATED')
    if type(scope_id) is not int or scope_id!=APPLICATION_SCOPE:raise ChatAIError('PERMISSION_DENIED')
    if not (can_view(user) or can_access_hilton_reports(user)):raise ChatAIError('PERMISSION_DENIED')
    return user


def allowed_resources(user):
    resources=set(COMMON_RESOURCES) if can_view(user) else set()
    if can_access_hilton_reports(user):resources.add('hilton_report')
    if user.is_staff:resources.add('user')
    return resources


def capabilities(user, scope_id=APPLICATION_SCOPE):
    result={'read'}
    result.update('read_'+name for name in allowed_resources(user))
    if can_view(user):
        result.add('financial')
        for name,check in [('create',can_create),('update',can_update),('delete',can_delete)]:
            if check(user):result.add(name)
    if can_access_hilton_reports(user):result.add('hilton')
    if user.is_staff:result.add('staff')
    return result


def authorize_resource(user, scope_id, resource):
    if scope_id!=APPLICATION_SCOPE or resource not in allowed_resources(user):raise ChatAIError('PERMISSION_DENIED')


def authorize_change(user, scope_id, resource, operation):
    from .resources import RESOURCES
    authorize_resource(user,scope_id,resource)
    if resource not in RESOURCES or not RESOURCES[resource].editable or operation not in ('update','delete') or operation not in capabilities(user):raise ChatAIError('PERMISSION_DENIED')


def authorization_stamp(user_id, scope_id=APPLICATION_SCOPE):
    user=authorize(user_id,scope_id)
    payload=['reservation',user.pk,user.is_staff,user.is_superuser,sorted(capabilities(user))]
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
