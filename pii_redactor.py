import re
import spacy
from faker import Faker
from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerResult, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider

# ==========================================
# 1. Consistent PII Mapping Registry
# ==========================================

class PiiRegistry:
    def __init__(self):
        # Using Indian locale for realistic local name generations since the prospectus is Indian
        self.faker = Faker('en_IN')
        self.mappings = {}  # original_text_lower -> fake_text
        self.type_mappings = {}  # original_text_lower -> entity_type

    def _generate_fake_email(self, original_email):
        username, domain = original_email.split("@", 1)
        user_tokens = re.split(r'[._-]', username.lower())
        
        # Check if we can find a matching name in our registry
        matched_fake_name = None
        for orig_name, fake_name in self.mappings.items():
            orig_name_tokens = orig_name.lower().split()
            # Check overlap of name tokens in the email username
            overlap = [t for t in user_tokens if any(ot in t or t in ot for ot in orig_name_tokens if len(ot) > 2)]
            if overlap:
                matched_fake_name = fake_name
                break
                
        if matched_fake_name:
            fake_user = matched_fake_name.lower().replace(" ", ".")
        else:
            fake_name = self.faker.name()
            fake_user = fake_name.lower().replace(" ", ".")
            
        return f"{fake_user}@example.com"

    def get_fake_value(self, original_text, entity_type):
        key = original_text.strip()
        # Remove trailing punctuation or whitespace for mapping keys
        clean_key = re.sub(r'^[^\w]+|[^\w]+$', '', key)
        if not clean_key:
            clean_key = key
        key_lower = clean_key.lower()

        if key_lower in self.mappings:
            return self.mappings[key_lower]

        # Generate fake value based on entity type
        fake_val = ""
        if entity_type == "PERSON":
            fake_val = self.faker.name()
        elif entity_type == "EMAIL_ADDRESS":
            fake_val = self._generate_fake_email(clean_key)
        elif entity_type == "PHONE_NUMBER":
            if clean_key.startswith("+91") or clean_key.startswith("91"):
                # Clean and keep +91 structure
                fake_val = "+91 " + "".join(self.faker.msisdn()[3:])
            else:
                fake_val = self.faker.phone_number()
        elif entity_type == "COMPANY":
            fake_val = self.faker.company()
            # Ensure it sounds like a company and retains similar suffix structure
            if "limited" in key_lower and "limited" not in fake_val.lower():
                fake_val += " Limited"
            elif "pvt" in key_lower and "private" not in fake_val.lower():
                fake_val += " Private Limited"
        elif entity_type == "ADDRESS":
            # Clean newlines and double commas
            fake_val = self.faker.address().replace("\n", ", ")
        elif entity_type == "DATE_OF_BIRTH":
            dob = self.faker.date_of_birth(minimum_age=25, maximum_age=80)
            # Try to match the format of the original string
            if re.search(r'[a-zA-Z]', clean_key):
                fake_val = dob.strftime("%B %d, %Y")
            else:
                fake_val = dob.strftime("%d/%m/%Y")
        elif entity_type == "IP_ADDRESS":
            fake_val = self.faker.ipv4()
        elif entity_type == "US_SSN":
            fake_val = self.faker.ssn()
        elif entity_type == "CREDIT_CARD":
            fake_val = self.faker.credit_card_number()
        else:
            fake_val = f"[REDACTED_{entity_type}]"

        # Apply capitalization matching
        if clean_key.isupper():
            fake_val = fake_val.upper()

        self.mappings[key_lower] = fake_val
        self.type_mappings[key_lower] = entity_type
        return fake_val

# ==========================================
# 2. Custom Presidio Recognizers
# ==========================================

class CompanyRecognizer(EntityRecognizer):
    def __init__(self):
        super().__init__(supported_entities=["COMPANY"])
        # Suffix-based regex for Indian and global companies
        self.company_regex = re.compile(
            r"\b[A-Z0-9][A-Za-z0-9&\s.,-]{2,60}\s+(?:Limited|Private Limited|Pvt\.?\s*Ltd\.?|LLP|LTD|Inc\.?|Corp\.?|Corporation|Bank|Securities|Holdings|Solutions)\b",
            re.UNICODE
        )

    def analyze(self, text, entities, nlp_artifacts=None):
        results = []
        # 1. Regex Match
        for match in self.company_regex.finditer(text):
            results.append(RecognizerResult(
                entity_type="COMPANY",
                start=match.start(),
                end=match.end(),
                score=0.85
            ))
        
        # 2. Extract ORG entities from spaCy
        if nlp_artifacts and nlp_artifacts.entities:
            for ent in nlp_artifacts.entities:
                if ent.label_ == "ORG":
                    start, end = ent.start_char, ent.end_char
                    # Only add if it does not overlap with existing company matches
                    overlap = False
                    for r in results:
                        if not (end <= r.start or start >= r.end):
                            overlap = True
                            break
                    if not overlap:
                        results.append(RecognizerResult(
                            entity_type="COMPANY",
                            start=start,
                            end=end,
                            score=0.75
                        ))
        return results


class AddressRecognizer(EntityRecognizer):
    def __init__(self):
        super().__init__(supported_entities=["ADDRESS"])
        self.address_keywords = re.compile(
            r"\b(?:Flat|Plot|House|Shop|Building|Tower|Office|Block|No\.?|Opposite|Opp\.?|Near|Behind|Beside|Floor|Road|Street|Lane|Nagar|Wadi|Chakan|Khed|Pune|Mumbai|Delhi|Bangalore|Kolkata|Chennai|Maharashtra|India|Gopal House)\b",
            re.IGNORECASE
        )
        self.pincode_regex = re.compile(r"\b\d{6}\b|\b\d{3}\s?\d{3}\b")
        # Regex matching structured address blocks
        self.address_regex = re.compile(
            r"\b\d+[-/a-zA-Z0-9\s,]{0,12}\s+(?:Floor|Flat|Plot|Shop|Building|Tower|Office|Block|House|Opposite|Opp\.?|Near|Behind|Beside|Road|Street|Lane|Nagar|Wadi|Chakan|Khed|Pune|Mumbai|Delhi|Bangalore|Kolkata|Chennai|Maharashtra|India|Gopal House)[a-zA-Z0-9\s,()./&–-]{10,200}(?:\b\d{3}\s?\d{3}\b|\bIndia\b|\bMaharashtra\b)",
            re.UNICODE | re.IGNORECASE
        )

    def analyze(self, text, entities, nlp_artifacts=None):
        results = []
        # 1. Regex Match
        for match in self.address_regex.finditer(text):
            results.append(RecognizerResult(
                entity_type="ADDRESS",
                start=match.start(),
                end=match.end(),
                score=0.85
            ))

        # 2. Extract GPE, LOC, FAC entities from spaCy as potential addresses if context matches
        if nlp_artifacts and nlp_artifacts.entities:
            for ent in nlp_artifacts.entities:
                if ent.label_ in ["GPE", "LOC", "FAC"]:
                    start, end = ent.start_char, ent.end_char
                    # Check overlap with regex matches
                    overlap = False
                    for r in results:
                        if not (end <= r.start or start >= r.end):
                            overlap = True
                            break
                    if not overlap:
                        # Scan context around entity
                        context_start = max(0, start - 50)
                        context_end = min(len(text), end + 50)
                        context = text[context_start:context_end]
                        if self.address_keywords.search(context) or self.pincode_regex.search(context):
                            results.append(RecognizerResult(
                                entity_type="ADDRESS",
                                start=start,
                                end=end,
                                score=0.70
                            ))
        return results


class DateOfBirthRecognizer(EntityRecognizer):
    def __init__(self):
        super().__init__(supported_entities=["DATE_OF_BIRTH"])
        # Matches dates where year is 1900-2015
        self.date_patterns = [
            # DD/MM/YYYY or DD-MM-YYYY
            re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-](?:19\d{2}|20[0-1]\d)\b"),
            # YYYY-MM-DD
            re.compile(r"\b(?:19\d{2}|20[0-1]\d)[/-]\d{1,2}[/-]\d{1,2}\b"),
            # Month DD, YYYY or DD Month YYYY
            re.compile(
                r"\b(?:\d{1,2}\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:\s*,\s*|\s+)(?:19\d{2}|20[0-1]\d)\b",
                re.IGNORECASE
            ),
            re.compile(
                r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(?:19\d{2}|20[0-1]\d)\b",
                re.IGNORECASE
            )
        ]

    def analyze(self, text, entities, nlp_artifacts=None):
        results = []
        for pattern in self.date_patterns:
            for match in pattern.finditer(text):
                results.append(RecognizerResult(
                    entity_type="DATE_OF_BIRTH",
                    start=match.start(),
                    end=match.end(),
                    score=0.85
                ))
        return results


class NameSalutationRecognizer(EntityRecognizer):
    def __init__(self):
        super().__init__(supported_entities=["PERSON"])
        self.salutation_regex = re.compile(
            r"\b(?:Mr\.?|Ms\.?|Mrs\.?|Dr\.?|Shri|Smt\.?|Late)\s+([A-Z][a-zA-Z']*(?:\s+[A-Z][a-zA-Z']*){1,3})\b",
            re.UNICODE
        )

    def analyze(self, text, entities, nlp_artifacts=None):
        results = []
        for match in self.salutation_regex.finditer(text):
            results.append(RecognizerResult(
                entity_type="PERSON",
                start=match.start(1),
                end=match.end(1),
                score=0.90
            ))
        return results

# ==========================================
# 3. Main PiiRedactor Engine
# ==========================================

class PiiRedactor:
    def __init__(self):
        self.registry = PiiRegistry()
        
        # Configure Presidio Analyzer to use spaCy
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]
        })
        nlp_engine = provider.create_engine()
        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
        
        # Add custom recognizers
        self.analyzer.registry.add_recognizer(CompanyRecognizer())
        self.analyzer.registry.add_recognizer(AddressRecognizer())
        self.analyzer.registry.add_recognizer(DateOfBirthRecognizer())
        self.analyzer.registry.add_recognizer(NameSalutationRecognizer())
        
        # Custom phone patterns for Indian format (+91 or space-separated)
        indian_phone = Pattern(
            name="indian_phone",
            regex=r"\b(?:\+?91[\s-]?)?[6789]\d{9}\b|\b(?:\+?91[\s-]?)?\d{2,4}[\s-]?\d{6,8}\b",
            score=0.85
        )
        self.analyzer.registry.add_recognizer(PatternRecognizer(
            supported_entity="PHONE_NUMBER", 
            patterns=[indian_phone]
        ))

    def analyze_text(self, text):
        """
        Scans text and returns resolved, non-overlapping PII detection results.
        """
        if not text.strip():
            return []
            
        entities = [
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "COMPANY", "ADDRESS", 
            "DATE_OF_BIRTH", "IP_ADDRESS", "US_SSN", "CREDIT_CARD"
        ]
        
        results = self.analyzer.analyze(text=text, entities=entities, language="en")
        
        # Resolve overlaps
        resolved = self._resolve_overlaps(results)
        
        # Convert to dictionary format
        pii_matches = []
        for r in resolved:
            pii_text = text[r.start:r.end]
            fake_val = self.registry.get_fake_value(pii_text, r.entity_type)
            pii_matches.append({
                "start": r.start,
                "end": r.end,
                "entity_type": r.entity_type,
                "original": pii_text,
                "fake": fake_val
            })
            
        # Sort by start index in descending order
        pii_matches.sort(key=lambda x: x["start"], reverse=True)
        return pii_matches

    def _resolve_overlaps(self, results):
        # Sort by start index ascending, then span length descending
        sorted_results = sorted(results, key=lambda x: (x.start, -(x.end - x.start)))
        resolved = []
        for r in sorted_results:
            overlap = False
            for existing in resolved:
                # Check intersection
                if not (r.end <= existing.start or r.start >= existing.end):
                    overlap = True
                    # Keep the one with the higher score or length
                    if r.score > existing.score or (r.score == existing.score and (r.end - r.start) > (existing.end - existing.start)):
                        resolved.remove(existing)
                        resolved.append(r)
                    break
            if not overlap:
                resolved.append(r)
        return resolved

    def redact_text(self, text):
        """
        Redacts simple raw text, replacing all PII.
        """
        matches = self.analyze_text(text)
        redacted = text
        for m in matches:
            redacted = redacted[:m["start"]] + m["fake"] + redacted[m["end"]:]
        return redacted
