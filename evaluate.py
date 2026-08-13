import time
from pii_redactor import PiiRedactor

# Ground truth test dataset containing all 9 target PII types
TEST_DATA = [
    {
        "text": "Registered Office: 11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka - Khed, Pune – 410 501, Maharashtra, India;",
        "pii": [
            {"entity_type": "ADDRESS", "value": "11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka - Khed, Pune – 410 501, Maharashtra, India"}
        ]
    },
    {
        "text": "Corporate Office: 201, Tower 2, Montreal Business Centre, Off Pallod Farms, Baner, Pune – 411 045, Maharashtra, India;",
        "pii": [
            {"entity_type": "ADDRESS", "value": "201, Tower 2, Montreal Business Centre, Off Pallod Farms, Baner, Pune – 411 045, Maharashtra, India"}
        ]
    },
    {
        "text": "Contact Person: Sarthak Malvadkar, Company Secretary and Compliance Officer; Telephone: + 91 20 4505 3237; E-mail: cs.connect@kshinternational.com",
        "pii": [
            {"entity_type": "PERSON", "value": "Sarthak Malvadkar"},
            {"entity_type": "PHONE_NUMBER", "value": "+ 91 20 4505 3237"},
            {"entity_type": "EMAIL_ADDRESS", "value": "cs.connect@kshinternational.com"}
        ]
    },
    {
        "text": "Hingne Tare & Associates Flat No. 102, Sai Complex Shaniwar Peth, Pune – 411 030 Maharashtra, India E-mail: hingnetare@gmail.com Firm registration number: 116417W",
        "pii": [
            {"entity_type": "COMPANY", "value": "Hingne Tare & Associates"},
            {"entity_type": "ADDRESS", "value": "Flat No. 102, Sai Complex Shaniwar Peth, Pune – 411 030 Maharashtra, India"},
            {"entity_type": "EMAIL_ADDRESS", "value": "hingnetare@gmail.com"}
        ]
    },
    {
        "text": "Certain of our SMs including, Sandesh Bhagwat, CEO, Amod Joshi, CFO, Sarthak Malvadkar, CS and Compliance Officer, and Girish Bhandary, Director.",
        "pii": [
            {"entity_type": "PERSON", "value": "Sandesh Bhagwat"},
            {"entity_type": "PERSON", "value": "Amod Joshi"},
            {"entity_type": "PERSON", "value": "Sarthak Malvadkar"},
            {"entity_type": "PERSON", "value": "Girish Bhandary"}
        ]
    },
    {
        "text": "The statutory auditors are Kirtane & Pandit, LLP, Chartered Accountants 5th Floor, Gopal House Opposite Harshal Hall, above HDFC Limited Karve Road, Pune – 411 038 Maharashtra, India",
        "pii": [
            {"entity_type": "COMPANY", "value": "Kirtane & Pandit, LLP"},
            {"entity_type": "ADDRESS", "value": "5th Floor, Gopal House Opposite Harshal Hall, above HDFC Limited Karve Road, Pune – 411 038 Maharashtra, India"},
            {"entity_type": "COMPANY", "value": "HDFC Limited"}
        ]
    },
    {
        "text": "Please contact us at +91-20-26234000 or write to pravin.teli2@hdfcbank.com. The registrar is Link Intime India Private Limited.",
        "pii": [
            {"entity_type": "PHONE_NUMBER", "value": "+91-20-26234000"},
            {"entity_type": "EMAIL_ADDRESS", "value": "pravin.teli2@hdfcbank.com"},
            {"entity_type": "COMPANY", "value": "Link Intime India Private Limited"}
        ]
    },
    {
        "text": "He was born on October 12, 1974. His SSN is 453-29-1092 and his credit card number is 4532-9012-9843-1120.",
        "pii": [
            {"entity_type": "DATE_OF_BIRTH", "value": "October 12, 1974"},
            {"entity_type": "US_SSN", "value": "453-29-1092"},
            {"entity_type": "CREDIT_CARD", "value": "4532-9012-9843-1120"}
        ]
    },
    {
        "text": "The server can be reached at the IP address 192.168.1.105 or 10.0.0.1.",
        "pii": [
            {"entity_type": "IP_ADDRESS", "value": "192.168.1.105"},
            {"entity_type": "IP_ADDRESS", "value": "10.0.0.1"}
        ]
    },
    {
        "text": "Rohan Dey lives at Flat No. 12, Shanti Vihar, Mumbai 400001, Maharashtra and his email is rohan.dey@gmail.com and cell phone is +91 9876543210.",
        "pii": [
            {"entity_type": "PERSON", "value": "Rohan Dey"},
            {"entity_type": "ADDRESS", "value": "Flat No. 12, Shanti Vihar, Mumbai 400001, Maharashtra"},
            {"entity_type": "EMAIL_ADDRESS", "value": "rohan.dey@gmail.com"},
            {"entity_type": "PHONE_NUMBER", "value": "+91 9876543210"}
        ]
    },
    {
        "text": "Rashi Patil represents Nuvama Wealth Management Limited which has its registered office at Montreal Business Centre, Pune.",
        "pii": [
            {"entity_type": "PERSON", "value": "Rashi Patil"},
            {"entity_type": "COMPANY", "value": "Nuvama Wealth Management Limited"},
            {"entity_type": "ADDRESS", "value": "Montreal Business Centre, Pune"}
        ]
    }
]

def evaluate():
    print("Initializing PII Redactor...")
    t0 = time.time()
    redactor = PiiRedactor()
    print(f"Redactor initialized in {time.time()-t0:.2f}s\n")
    
    # Initialize metrics structure
    categories = [
        "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "COMPANY", "ADDRESS", 
        "DATE_OF_BIRTH", "IP_ADDRESS", "US_SSN", "CREDIT_CARD"
    ]
    
    stats = {cat: {"tp": 0, "fp": 0, "fn": 0} for cat in categories}
    overall = {"tp": 0, "fp": 0, "fn": 0}
    
    print("Running evaluation on test suite...")
    for idx, item in enumerate(TEST_DATA):
        text = item["text"]
        gt_list = item["pii"]
        
        # Run detection
        predictions = redactor.analyze_text(text)
        
        # Track which predictions and ground truths are matched
        matched_gt = set()
        matched_pred = set()
        
        # Step 1: Find True Positives
        for gt_idx, gt in enumerate(gt_list):
            gt_type = gt["entity_type"]
            gt_val = gt["value"].lower()
            
            for p_idx, pred in enumerate(predictions):
                pred_type = pred["entity_type"]
                pred_val = pred["original"].lower()
                
                # Check for overlap or substring match with same entity type
                if gt_type == pred_type:
                    # Check substring match or overlap
                    if gt_val in pred_val or pred_val in gt_val or (pred["start"] >= text.lower().find(gt_val) and pred["end"] <= text.lower().find(gt_val) + len(gt_val)):
                        stats[gt_type]["tp"] += 1
                        overall["tp"] += 1
                        matched_gt.add(gt_idx)
                        matched_pred.add(p_idx)
                        break
        
        # Step 2: Find False Negatives (unmatched ground truths)
        for gt_idx, gt in enumerate(gt_list):
            if gt_idx not in matched_gt:
                gt_type = gt["entity_type"]
                stats[gt_type]["fn"] += 1
                overall["fn"] += 1
                print(f"  [FN] Missed {gt_type}: '{gt['value']}' in Sentence {idx+1}")
                
        # Step 3: Find False Positives (unmatched predictions)
        for p_idx, pred in enumerate(predictions):
            if p_idx not in matched_pred:
                pred_type = pred["entity_type"]
                stats[pred_type]["fp"] += 1
                overall["fp"] += 1
                print(f"  [FP] Incorrect {pred_type}: '{pred['original']}' in Sentence {idx+1}")

    print("\n" + "="*50)
    print("EVALUATION REPORT")
    print("="*50)
    print(f"| {'PII Type':<15} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Precision':<9} | {'Recall':<9} | {'F1-Score':<9} |")
    print(f"|{'-'*17}|{'-'*6}|{'-'*6}|{'-'*6}|{'-'*11}|{'-'*11}|{'-'*11}|")
    
    for cat in categories:
        tp = stats[cat]["tp"]
        fp = stats[cat]["fp"]
        fn = stats[cat]["fn"]
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
        recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        print(f"| {cat:<15} | {tp:<4} | {fp:<4} | {fn:<4} | {precision:.4f}    | {recall:.4f}    | {f1:.4f}    |")
        
    # Overall metrics
    o_tp = overall["tp"]
    o_fp = overall["fp"]
    o_fn = overall["fn"]
    o_precision = o_tp / (o_tp + o_fp) if (o_tp + o_fp) > 0 else 1.0
    o_recall = o_tp / (o_tp + o_fn) if (o_tp + o_fn) > 0 else 1.0
    o_f1 = 2 * o_precision * o_recall / (o_precision + o_recall) if (o_precision + o_recall) > 0 else 0.0
    
    # Calculate a simple accuracy metric: entity-level IoU (TP / (TP + FP + FN))
    o_accuracy = o_tp / (o_tp + o_fp + o_fn) if (o_tp + o_fp + o_fn) > 0 else 1.0
    
    print(f"|{'-'*17}|{'-'*6}|{'-'*6}|{'-'*6}|{'-'*11}|{'-'*11}|{'-'*11}|")
    print(f"| {'OVERALL':<15} | {o_tp:<4} | {o_fp:<4} | {o_fn:<4} | {o_precision:.4f}    | {o_recall:.4f}    | {o_f1:.4f}    |")
    print("="*50)
    print(f"Entity-level Accuracy (IoU): {o_accuracy:.4f}")
    
if __name__ == "__main__":
    evaluate()
