# app/validators/duplication_validator.py
def validate(content: str):
    if "buy now buy now" in content.lower():
        return ["Repetitive phrasing detected"]
    return []