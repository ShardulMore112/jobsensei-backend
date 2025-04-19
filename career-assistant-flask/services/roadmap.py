import os
import json
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

def load_documents(resume_path, skills_path=None):
    data = []
    loaders = {
        ".pdf": PyPDFLoader,
        ".docx": Docx2txtLoader,
        ".txt": TextLoader,
        ".md": TextLoader
    }

    for path in [resume_path, skills_path]:
        if path and os.path.exists(path):
            ext = os.path.splitext(path)[-1].lower()
            loader_class = loaders.get(ext)
            if loader_class:
                loader = loader_class(path)
                data.extend(loader.load())
    return data

def setup_career_advisor(resume_path, skills_path=None, ref_docs_folder=None):
    data = load_documents(resume_path, skills_path)

    if ref_docs_folder and os.path.exists(ref_docs_folder):
        for file in os.listdir(ref_docs_folder):
            full_path = os.path.join(ref_docs_folder, file)
            if full_path.endswith((".pdf", ".docx", ".txt", ".md")):
                data.extend(load_documents(full_path))

    if not data:
        raise ValueError("No valid documents provided")

    splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=500)
    docs = splitter.split_documents(data)

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings, persist_directory="./career_vector_db")
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 15})

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7, max_tokens=2000)

    # Escape curly braces with double {{ and }} for prompt safety
    system_prompt = (
        "You are a career advisor AI assistant. Analyze the provided resume and documents "
        "to create a clear, concise career roadmap in JSON format. The JSON must follow this structure:\n\n"
        "{{\n"
        '  "career_goal": "User\'s specified goal",\n'
        '  "roadmap": [\n'
        "    {{\n"
        '      "step": 1,\n'
        '      "title": "Step title",\n'
        '      "description": "Brief description",\n'
        '      "duration": "Estimated time",\n'
        '      "resources": ["Resource 1", "Resource 2"]\n'
        "    }}\n"
        "  ]\n"
        "}}"
    )

    prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "Based on the following resume and documents:\n{context}\n\nUser's goal: {input}"),
])


    qa_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, qa_chain)

    return rag_chain

def extract_json_response(response_text):
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = response_text[start:end]
            return json.loads(json_str)
        return {"error": "No valid JSON found."}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format."}

def get_roadmap_json(rag_chain, career_goal):
    query = f"Create a career roadmap in JSON format for my goal of: {career_goal}"
    response = rag_chain.invoke({"input": query})
    return extract_json_response(response.get("answer", ""))
