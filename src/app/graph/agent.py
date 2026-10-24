from typing import Annotated, Literal
import os
import uuid
import httpx
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import Literal, TypedDict, Annotated
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")

JOBPULSE_URL = os.getenv('JOBPULSE_URL', 'http://localhost:8888')

class IntentClassifier(BaseModel):
    message_intent: Literal['job', 'classify_AMP'] = Field(..., description='Classify whether user wants to search for job or do AMP classification')

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_intent: str | None

def classify_intent(state: State):
    structured_llm = llm.with_structured_output(IntentClassifier)

    result = structured_llm.invoke([
        {
            'role': 'system', 'content': 'Determine / classify whether the user wants to find job ("job") or do AMP classification ("classify_AMP").'
        },
        {
            'role': 'user', 'content': state['messages'][-1].content
        }
    ])

    return {'message_intent': result.message_intent}

def search_jobs(query: str, k: int = 5) -> list[dict]:
    response = httpx.post(f'{JOBPULSE_URL}/search', json={'query': query, 'k': k}, timeout=30)
    response.raise_for_status()

    return response.json()['job_list']

def job_search(state: State):
    try:
        jobs = search_jobs(state['messages'][-1].content)
    except httpx.HTTPError as e:
        print(f'JobPulse search error: {e}')
        jobs = None

    if jobs is None:
        context = 'The job search service is unavailable. Tell the user to try again later.'
    elif not jobs:
        context = 'No matching jobs were found. Tell the user and suggest refining the query.'
    else:
        context = f'Present these jobs to the user, including title, company, location and url:\n{jobs}'

    messages = [{
        'role': 'system', 'content': f'You are a job search assistant. {context}'
    }] + state['messages']

    return {'messages': [llm.invoke(messages)]}

def classify_AMP(state: State):
    messages = [{
        'role': 'system', 'content': 'No matter what user says, always say "AMP classify agent"'
    }] + state['messages']

    return {'messages': [llm.invoke(messages)]}

graph_builder = StateGraph(State)

# Node
graph_builder.add_node('intent_classifier', classify_intent)
graph_builder.add_node('job', job_search)
graph_builder.add_node('AMP_classify', classify_AMP)
# Edge
graph_builder.add_edge(START, 'intent_classifier')
graph_builder.add_conditional_edges('intent_classifier', lambda state: state['message_intent'], {
    'job': 'job',
    'classify_AMP': "AMP_classify"
})

graph_builder.add_edge('job', END)
graph_builder.add_edge('AMP_classify', END)

checkpointer = InMemorySaver()

chat_graph = graph_builder.compile(checkpointer=checkpointer)
config = {'configurable': {'thread_id': uuid.uuid4()}}

def agent_chat(user_message: str):
    response = chat_graph.invoke({
        'messages': [{'role': 'user', 'content': user_message}]
        }, 
        config = config
        )

    return response['messages'][-1].text