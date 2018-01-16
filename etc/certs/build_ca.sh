#!/bin/bash
# Build an example CA, server & client certs.

set -x
BASEDN="/C=XX/L=Default City/O=Default Company Ltd/OU=Test CA"

rm -f *.csr *.crt *.key *.srl

# Generate CA
openssl genrsa -out CA.key 2048
openssl req -x509 -new -batch -nodes -subj "${BASEDN}" -key CA.key -sha256 -days 3650 -out CA.crt

# Server Cert
openssl genrsa -out server.key 2048
openssl req -new -batch -key server.key -subj "${BASEDN}/CN=localhost" -out server.csr
openssl x509 -req -CA CA.crt -CAkey CA.key -CAcreateserial -days 365 -sha256 -in server.csr -out server.crt

# Client Cert
openssl genrsa -out client.key 2048
openssl req -new -batch -key client.key -subj "${BASEDN}/CN=client user" -out client.csr
openssl x509 -req -CA CA.crt -CAkey CA.key -CAcreateserial -days 365 -sha256 -in client.csr -out client.crt

