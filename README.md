# TRK-TechAssistant

# Abou the Platform
Local Whatsapp data archive system with a GUI and an AI feature that archives the invoice data received by image/pdf files
In our system we assume the main admin user is archiving all data received from the groups joined.

## AI-Features
### OCR Invoice readers

#### **Description**
Takes an image/pdf file and returns a JSON structured output text.

#### **Usage** 
```
pip install -r ai_features/requirement.txt
```

```
python ai_features/main.py /path/to/file.pdf
```