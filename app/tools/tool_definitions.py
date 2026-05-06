# mdoele toolları tanımlamamız lazım 
# tool isimleri, hang parametreleri aldığından vs bahsedioruz

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "weather_tool",
            "description": "Verilen şehrin güncel hava durumunu getirir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Hava durumu sorgulanacak şehir adı"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "company_info_tool",
            "description": "Şirket ile ilgili temel bilgileri getirir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Sorgulanacak konu. Örnek: mesai, adres, telefon"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_numbers",
            "description": "İki sayıyı toplar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "integer",
                        "description": "Birinci sayı"
                    },
                    "b": {
                        "type": "integer",
                        "description": "İkinci sayı"
                    }
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "subtract_numbers",
            "description": "İki sayı arasındaki farkı hesaplar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "integer",
                        "description": "Birinci sayı"
                    },
                    "b": {
                        "type": "integer",
                        "description": "İkinci sayı"
                    }
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "multiply_numbers",
            "description": "İki sayıyı çarpar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "integer",
                        "description": "Birinci sayı"
                    },
                    "b": {
                        "type": "integer",
                        "description": "İkinci sayı"
                    }
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "divide_numbers",
            "description": "Bir sayıyı başka bir sayıya böler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "integer",
                        "description": "Bölünen sayı"
                    },
                    "b": {
                        "type": "integer",
                        "description": "Bölen sayı"
                    }
                },
                "required": ["a", "b"]
            }
        }
    }
]