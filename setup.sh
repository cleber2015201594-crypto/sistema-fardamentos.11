#!/bin/bash
mkdir -p /tmp/.streamlit

echo "\
[server]\n\
headless = true\n\
port = $PORT\n\
enableCORS = false\n\
\n\
" > /tmp/.streamlit/config.toml
