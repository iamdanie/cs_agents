import requests
from bs4 import BeautifulSoup
from openai import OpenAI

def parse_page_content(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    content = soup.body
    
    for post_header in content.find_all('div', class_='single-post-header'):
        post_header.decompose()
        
    for sidebar in content.find_all('div', class_='sidebar'):
        sidebar.decompose()
        
    for header in content.find_all('header'):
        header.decompose()
        
    for nav in content.find_all('nav'):
        nav.decompose()
        
    for footer in content.find_all('footer'):
        footer.decompose()
        
    for h3 in content.find_all('h3'):
        if h3.string: 
            h3.string.replace_with(f"- {h3.string.upper()}")
        else:
            inner_text = h3.get_text(separator=' ', strip=True)
            h3.clear()
            h3.append(f"- {inner_text.upper()}\n")
            
    for li in content.find_all('li'):
        if li.string: 
            li.string.replace_with(f"-- {li.string.upper()}")
        else:
            inner_text = li.get_text(separator=' ', strip=True)
            li.clear()
            li.append(f"-- {inner_text.upper()}\n")
            
    for h2 in content.find_all('h2'):
        if h2.string: 
            h2.string.replace_with(f"{h3.string.upper()}\n")
        else:
            inner_text = h2.get_text(separator=' ', strip=True)
            h2.clear()
            h2.append(f"{inner_text.upper()}\n")
    
    text = content.get_text(separator='\n', strip=True)
    return text

def initialize_bot_stores(client: OpenAI, knowledge_base_text: str):
    """Initialize the vector stores needed by the bot."""
    
    file = client.files.create(
        file=open("resources/car_stock.json", "rb"),
        purpose="assistants"
    )
    file_id = file.id
    
    vector_store = client.vector_stores.create(name="Car Stock Search")
    
    client.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=file_id,
    )
    
    with open("resources/kavak_knowledge_base.txt", "w", encoding="utf-8") as blob:
        blob.write(knowledge_base_text)
        
    kb_file = client.files.create(
        file=open("resources/kavak_knowledge_base.txt", "rb"),
        purpose="assistants"
    )
    kb_file_id = kb_file.id
    
    kb_vector_store = client.vector_stores.create(name="Kavak knowledge base")
    
    client.vector_stores.files.create(
        vector_store_id=kb_vector_store.id,
        file_id=kb_file_id,
    )
    
    return vector_store, kb_vector_store