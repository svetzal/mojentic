from mojentic.llm import ChatSession, LLMBroker

llm_broker = LLMBroker(model="llama3.3-70b-32k")
chat_session = ChatSession(llm_broker)

while True:
    query = input("Query: ")
    if not query:
        break
    else:
        response = chat_session.send(query)
        print(response)