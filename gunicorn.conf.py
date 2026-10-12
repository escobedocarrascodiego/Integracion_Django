# Gunicorn reads this file automatically from the working directory.
# Gunicorn instead of `runserver`, which is a development server.

bind = "0.0.0.0:8000"
workers = 2
# Threads let a worker keep serving while another request waits on Claude.
threads = 4
# A chat turn with several tool calls can take a while.
timeout = 120
accesslog = "-"
