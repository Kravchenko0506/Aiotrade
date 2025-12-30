FROM freqtradeorg/freqtrade:stable

USER root 
# Temporarily grants admin rights to install libraries

COPY requirements.txt /freqtrade/

RUN pip install --no-cache-dir -r /freqtrade/requirements.txt

USER ftuser
