"""Classify untrusted text without answering it, invoking a model or calling an API."""
import re
import unicodedata
from typing import Literal, TypedDict

Decision = Literal['allow', 'clarify', 'reject']
class ScopeResult(TypedDict):
    decision: Decision
    reason: str

OUTSIDE_SCOPE = 'I can help write or improve an email or WhatsApp message. Tell me who it’s for and what you want to say.'
CLARIFICATION = 'Who is this message for, and what do you want to tell them?'

def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKC', text)
    return ''.join(c for c in text if unicodedata.category(c) != 'Cf').strip()

def matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)

WRITE_ACTIONS = (
    r'लेख|पठाउ|पठाइ|जवाफ|अनुवाद',
    r'\b(?:lekh\w*|pathau\w*|bhanid\w*)\b',
    r'\b(write|draft|compose|rewrite|rephrase|polish|proofread|reply|fix|correct|improve|translate|shorten|ask|tell)\b',
    r'\b(ezhuth\w*|eluth\w*|anupp\w*|keka\w*|kekka\w*|maang\w*|adag\w*|sang\w*)\b',
    r'எழுத|திருத்த|அனுப்ப|பதிலளி|மொழிபெயர்|கேட்க',
    r'लिख|लिह|पाठव|उत्तर|दुरुस्त|सुधार|जवाब|अनुवाद|माग|सांग',
    r'రాయ|వ్రాయ|సవరించ|సమాధానం|అనువదించ|అడగ',
    r'اكتب|أكتب|صياغة|صحح|صحّح|ترجم|اختصر|أطلب|اطلب',
)
MESSAGE_TYPES = (
    r'इमेल|सन्देश|जवाफ',
    r'\b(e-?mail|whats\s*app|message|msg|letter|reply|draft)\b',
    r'மின்னஞ்சல்|செய்தி|கடிதம்|பதில்|ईमेल|मेल|संदेश|मैसेज|पत्र|जवाब',
    r'ఈమెయిల్|మెయిల్|సందేశం|మెసేజ్|లేఖ|رسالة|بريد|إيميل|ايميل|واتساب',
)
RECIPIENTS = (
    r'म्यानेजर|प्रबन्धक|सहकर्मी|साथी',
    r'\b(?:sathi|sahakarmi|prabandhak|shikshak)\b',
    r'\b(manager|colleague|coworker|team|teacher|school|admin|friend|client|customer|supervisor|principal)\b',
    r'மேலாள|ஆசிரிய|பள்ளி|நண்ப|मैनेजर|शिक्षक|शाळ|मित्र|మేనేజర్|స్నేహిత|مدير|زميل|صديق|مدرس',
)
MESSAGE_PURPOSES = (
    r'बिदा|तलब|ढिलो|बैठक|भुक्तानी',
    r'\b(?:bida|bidha|talab|dhilo|baithak)\b',
    r'\b(leave|salary|late|permission|payment|interview|follow.?up|receipt|meeting|fee|installation|update|deadline)\b',
    r'\b(vidumurai|viduppu|sambalam|chhutti|sutti|selavu|kaam|pani|velai)\b',
    r'விடுப்பு|சம்பளம்|அனுமதி|தாமத|छुट्टी|वेतन|तनख्वाह|अनुमति|रजा|सुट्टी',
    r'సెలవు|జీతం|అనుమతి|ఆలస్యం|إجازة|راتب|إذن|تأخير|اجتماع',
)
DIRECT_QA = (
    r'^(?:कृपया\s*)?(?:के हो|किन|कसरी|कहिले|कहाँ|को हो|बुझा|व्याख्या|अनुसन्धान|गणना)',
    r'^(?:kripaya\s+)?(?:ke ho|kina|kasari|kahile|kaha|bujhau|anusandhan)\b',
    r'^(?:(?:please|can you|could you|would you)\s+)?(?:office:\s*)?(?:what|why|who|when|where|how|explain|research|calculate|solve|summari[sz]e|teach me|tell me about)\b',
    r'^(?:please\s+)?(?:write|generate)\s+(?:an?\s+)?(?:essay|story|poem|code)\b',
    r'^give me\b.*\b(recipe|horoscope|stock price)\b',
    r'^(என்ன|ஏன்|எப்படி|விளக்கு|ஆராய்ச்சி)',
    r'^(क्या|क्यों|कैसे|समझाओ|अनुसंधान|शोध करो|संशोधन करा)',
    r'^(ఏమిటి|ఎందుకు|ఎలా|వివరించ|పరిశోధన)',
    r'^(ما هو|ما هي|لماذا|كيف|اشرح|احسب|ابحث)',
)
MIXED_RESEARCH = (
    r'(?:^|र\s+|त्यसपछि\s+)(?:अनुसन्धान|खोजी)\s*(?:गर|गरेर|गर्न)',
    r'(?:^|\b(?:ra|ani|tyaspachi)\s+)(?:research|anusandhan|khoji)\s*(?:gara|garera|garnu)\b',
    r'(?:^|\b(?:and|then|also|first|before|after)\s+)(?:please\s+)?(?:research|look up|search for|investigate)\b',
    r'\b(?:researching|look up|search the web|find the facts|email me the findings)\b',
    r'(?:^|[.!?]\s*)(?:explain|research|calculate|solve)\b',
    r'(?:மற்றும்|பிறகு).*ஆராய்ச்சி|(?:और|फिर).*शोध|(?:మరియు|తర్వాత).*పరిశోధన|(?:ثم|و).*ابحث',
)
# Attendance facts are valid message content even without a "write" verb.
# Require both a class/meeting context and an explicit inability to attend.
ATTENDANCE_CONTEXT = (
    r'\b(?:tuition|tution|class(?:es)?|lesson|meeting|training)\b',
    r'டியூஷ|டியுஷ|டியூச|வகுப்|பாடம்|கூட்ட',
)
ATTENDANCE_ABSENCE = (
    r"\b(?:cannot|can[’']t|couldn[’']t|unable to|not able to|won[’']t be able to)\s+(?:attend|come|join|make it)\b",
    r'(?:வர|கலந்து\s*கொள்ள|பங்கேற்க|(?:attend|அட்டெண்ட்)\s*(?:பண்ண|செய்ய))\s*(?:முடியாது|முடியவில்லை|இயலாது)',
    r'\b(?:vara|varave|kalandhuka|attend\s+panna)\s*(?:mudiyadhu|mudiyathu|mudiyala|mudiyavillai)\b',
)

# Evidence of supplied content, rather than a request for facts from the model.
SUPPLIED_CONTENT = (
    r'(?:म|हामी|मैले|हामीले)\s.{0,120}(?:छु|छौं|छौँ|सक्दिन|सक्दैन|सकेको|गरेँ|हुनेछ|भएको)',
    r'काम\s*(?:पूरा|सम्पन्न|सकिएको)',
    r'\b(?:i|we|it|the|my|our|he|she|they)\b.{0,140}\b(?:have|has|am|are|is|was|were|will|completed|installed|asked|sent|attached|received|pending|ready|done)\b',
    r'\b(?:please ask|please send|could you approve|i want to ask|the installation|the new version)\b',
    r'நிறுவப்பட்டது|முடிந்தது|அனுப்பிய|இணைத்த|வேலை|పూర్తయింది|పంపాను|काम पूर्ण|जोडले|تم تثبيت|أرفقت|اكتمل',
)
EMPTY_WRITING = re.compile(r'^(?:please\s+)?(?:write|draft|compose|improve|rewrite|polish|fix|correct|translate)(?:\s+(?:this|it|that|an?|the|email|message|draft|whatsapp|letter|for me|in english))*[.!?]*$', re.I)


def classify_scope(text: str, *, purpose: str = '', mode: str = 'draft') -> ScopeResult:
    if not isinstance(text, str):
        return {'decision': 'reject', 'reason': 'invalid_input'}
    text = normalize(text)
    if not text or EMPTY_WRITING.fullmatch(text):
        return {'decision': 'clarify', 'reason': 'missing_details'}
    if matches(DIRECT_QA, text) or matches(MIXED_RESEARCH, text):
        return {'decision': 'reject', 'reason': 'research_or_qa'}
    # "Ask my teacher to explain gravity" is a message, not an explanation request.
    if re.search(r'\b(?:email|message|draft)\s+(?:explaining|summari[sz]ing)\b', text, re.I) and not re.search(r'\b(?:facts|details|text|draft)\s*:', text, re.I):
        return {'decision': 'clarify', 'reason': 'missing_source_facts'}
    if mode in {'improve', 'translate'}:
        if len(text.split()) >= 4 or matches(SUPPLIED_CONTENT, text):
            return {'decision': 'allow', 'reason': 'existing_content'}
        return {'decision': 'clarify', 'reason': 'missing_details'}
    if matches(ATTENDANCE_CONTEXT, text) and matches(ATTENDANCE_ABSENCE, text):
        return {'decision': 'allow', 'reason': 'supplied_attendance_facts'}
    writing = matches(WRITE_ACTIONS, text)
    message = matches(MESSAGE_TYPES, text)
    purpose_signal = matches(MESSAGE_PURPOSES, text)
    recipient = matches(RECIPIENTS, text)
    if writing and (message or recipient) and (purpose_signal or len(text.split()) >= 8):
        return {'decision': 'allow', 'reason': 'writing_request'}
    if purpose and (len(text.split()) >= 3 or matches(SUPPLIED_CONTENT, text)):
        return {'decision': 'allow', 'reason': 'guided_details'}
    if matches(SUPPLIED_CONTENT, text):
        return {'decision': 'allow', 'reason': 'supplied_facts'}
    if recipient and purpose_signal and (writing or len(text.split()) >= 5):
        return {'decision': 'allow', 'reason': 'communication_intent'}
    return {'decision': 'clarify', 'reason': 'ambiguous_input'}
