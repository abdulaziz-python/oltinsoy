from pyngrok import ngrok

ngrok.connect(8000)
public_url = ngrok.connect(8000).public_url
print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:8000\"")
