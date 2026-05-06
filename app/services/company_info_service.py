# bu sahte şirket bilgisi tutuyor test amaçlı ekledim 

def get_company_info(topic: str) -> str:
    company_data={
        "mesai" : "mesai saatleri 09:00-18.00 arasındadır",
        "adres" : "adres: kahramanmaraş/onikişubat",
        "telefon" : "telefon numarası: 05555555555"
    }

    topic = topic.lower().strip()

    if topic in company_data:
        return company_data[topic]
    
    return "bilgi bulunmadı"