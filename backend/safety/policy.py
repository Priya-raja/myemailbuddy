"""Conservative, zero-model-call admission policy for everyday communication."""
import re
import unicodedata
from dataclasses import dataclass

from .heuristics import OK, assess_user_input, is_standalone_insult

from .scope import classify_scope, OUTSIDE_SCOPE, CLARIFICATION, normalize

# Broader multilingual/romanized signals supplement the supplied English rules.
ABUSE = re.compile(r"\b(fucking|idiot|stupid|kill you|threaten|blackmail|hack|bypass|password|otp|api[_ -]?key|secret key|poda|podi|loosu|madarchod|bhenchod|chutiya)\b|முட்டாள்|தேவடியா|चूतिया|मादरचोद|बेवकूफ|वेडा|మూర్ఖ|లంజ|غبي|حقير|كلمة المرور|رمز التحقق", re.I)

@dataclass(frozen=True)
class Admission:
    allowed: bool
    code: str
    message: str


def check_message(text: str, *, purpose: str = "", mode: str = "draft") -> Admission:
    normalized = unicodedata.normalize('NFKC', text)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Cf')
    if not normalized.strip():
        return Admission(False, 'needs_details', CLARIFICATION)
    assessment = assess_user_input(normalized)
    if assessment.action != OK or ABUSE.search(normalized) or is_standalone_insult(normalized):
        return Admission(False, 'unsafe_message', 'Please remove personal details, links, abusive language or instructions to bypass the rules, then try again. Your message was not sent to the writing AI.')
    scope = classify_scope(normalized, purpose=purpose, mode=mode)
    if scope['decision'] == 'reject':
        return Admission(False, 'out_of_scope', OUTSIDE_SCOPE)
    if scope['decision'] == 'clarify':
        question = 'What facts or existing text should the message include?' if scope['reason'] == 'missing_source_facts' else CLARIFICATION
        return Admission(False, 'needs_details', question)
    return Admission(True, 'allowed', '')
