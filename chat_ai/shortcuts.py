"""Permission-filtered EN/FR commands, descriptive searches and bare-command help."""
import re
from chat_ai_assistant.clarifications import message_language
from chat_ai_assistant.routing import normalized
from chat_ai_assistant.contracts import ChatAIError
from .security import capabilities
from .labels import RESOURCE_LABELS
MODULES=[('/reservations','reservation'),('/residences','building'),('/appartements','apartment'),('/couts','cost'),('/locaux','local'),('/loyers','rent'),('/hilton','hilton_report'),('/utilisateurs','user')]
ALIASES={'/bookings':'/reservations','/buildings':'/residences','/apartments':'/appartements','/costs':'/couts','/premises':'/locaux','/rents':'/loyers','/users':'/utilisateurs','/search':'/voir','/chercher':'/voir','/edit':'/modifier','/delete':'/supprimer','/help':'/aide','/summary':'/bilan'}

def shortcut_catalog(user,language='fr'):
    en=language=='en';caps=capabilities(user);items=[]
    examples={'reservation':('client Démo Atlas en janvier 2034','guest Demo Atlas in January 2034'),'building':('résidence Démo','Demo residence'),'apartment':('appartement Démo','Demo apartment'),'cost':('entretien en janvier 2034','maintenance in January 2034'),'local':('locaux disponibles','available premises'),'rent':('loyers enregistrés impayés en 2034','recorded unpaid rents in 2034'),'hilton_report':('rapports de janvier 2034','reports from January 2034'),'user':('Démo Exemple','Demo Example')}
    for command,resource in MODULES:
        if 'read_'+resource not in caps:continue
        items.append({'command':command,'title':RESOURCE_LABELS[resource][int(en)],'help':'Describe the name or period to find matching records.' if en else 'Décrivez le nom ou la période pour trouver les documents correspondants.','example':command+' '+examples[resource][int(en)]})
    additions=[('/aide','Aide des raccourcis','Shortcut help','read'),('/voir','Rechercher un document','Find a record','read'),('/modifier','Modifier après confirmation','Edit with confirmation','update'),('/supprimer','Supprimer après confirmation','Delete with confirmation','delete'),('/bilan','Indicateurs annuels','Annual figures','financial')]
    for command,fr,english,cap in additions:
        if cap not in caps:continue
        help_text='Describe the record; choose the matching result before a change.' if en else 'Décrivez le document ; choisissez le bon résultat avant une modification.'
        example=command+' '+(('reservation for Demo Atlas' if en else 'réservation du client Démo Atlas') if 'read_reservation' in caps else ('saved Hilton report' if en else 'rapport Hilton enregistré'))
        if command=='/bilan':
            help_text='Specify the annual metric and year. Reservation amounts, returned amounts and rents differ.' if en else 'Précisez l’indicateur annuel et l’année. Réservations, montants retournés et loyers sont différents.'
            example=command+' '+('paid rents in 2034' if en else 'loyers payés en 2034')
        if command=='/aide':help_text='Show permitted commands.' if en else 'Afficher les commandes autorisées.';example=command
        items.append({'command':command,'title':english if en else fr,'help':help_text,'example':example})
    return items

def suggestions(user,language='fr'):
    en=language=='en';caps=capabilities(user);items=[]
    for cap,fr,english in [('read_reservation','Retrouve une réservation par nom de client.','Find a reservation by guest name.'),('read_local','Montre les locaux disponibles.','Show available commercial premises.'),('read_cost','Affiche les derniers coûts enregistrés.','Show the latest recorded costs.'),('read_rent','Comment retrouver les loyers impayés ?','How do I find unpaid rents?'),('read_hilton_report','Affiche les derniers rapports Hilton enregistrés.','Show the latest saved Hilton reports.')]:
        if cap in caps:items.append(english if en else fr)
    return items[:5]

def shortcut_action(text,executor=None,interface_language='fr'):
    if not text.startswith('/'):return None
    parts=text.split(maxsplit=1);command=ALIASES.get(parts[0].casefold(),parts[0].casefold());arg=parts[1].strip() if len(parts)>1 else ''
    if command=='/' and not arg:command='/aide'
    language=message_language(text,interface_language);en=language=='en'
    catalog=shortcut_catalog(executor.authorize(),language);item=next((x for x in catalog if x['command']==command),None)
    if not item:
        if command in dict(MODULES) or command in ('/modifier','/supprimer','/bilan'):raise ChatAIError('PERMISSION_DENIED')
        return {'tool':'clarify','message':'Unknown command. Send /help.' if en else 'Commande inconnue. Envoyez /aide.'}
    if command=='/aide':return {'tool':'clarify','message':'\n'.join(x['command']+' : '+x['title'] for x in catalog)}
    resource=dict(MODULES).get(command)
    if resource and not arg:return {'tool':'search_records','arguments':{'resource':resource},'usage_message':item['help']+' '+item['example']}
    if not arg:return {'tool':'clarify','message':item['help']+' '+item['example']}
    return None

def reference_action(text,state):
    if not state.get('ids'):return None
    words=normalized(text).strip().rstrip('.!?');values={'first':1,'second':2,'third':3,'premier':1,'premiere':1,'deuxieme':2,'troisieme':3}
    match=re.fullmatch(r'(?:open (?:the )?|ouvre (?:le |la )?)(first|second|third|premier|premiere|deuxieme|troisieme)(?: one| result| resultat)?',words)
    return {'tool':'previous_results','arguments':{'operation':'open','index':values[match[1]]}} if match else None

def knowledge_action(text):
    words=normalized(text).strip()
    if len(text)<300 and not re.search(r'\d|\b(?:then|puis|ensuite|ignore|et|and|current|this|ce|cette)\b',words) and re.match(r'^(?:how (?:do i|to)|comment (?:creer|retrouver|trouver|modifier|supprimer|utiliser)|que signifie|what does)\b',words):return {'tool':'knowledge','arguments':{'query':text}}
    return None

def greeting_action(text):
    words=re.sub(r'\s+',' ',normalized(text).strip().rstrip('.!?').strip())
    if words in {'hello','hi','hey','good morning','good afternoon','good evening','hello there'}:return {'tool':'clarify','message':'Hello! How can I help you in Réservation?'}
    if words in {'bonjour','salut','bonsoir','coucou','bonjour a tous'}:return {'tool':'clarify','message':'Bonjour ! Comment puis-je vous aider dans Réservation ?'}
    if words in {'thanks','thank you','thank you very much'}:return {'tool':'clarify','message':'You’re welcome!'}
    if words in {'merci','merci beaucoup'}:return {'tool':'clarify','message':'Avec plaisir !'}
    return None
