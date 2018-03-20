#!/bin/bash
# Build an example CA, server & client certs.

set -x
BASEDN="/C=XX/L=Default City/O=Default Company Ltd/OU=Test CA"
# SAN for all certificates
export SAN=localhost

rm -rf certs
mkdir certs
cd certs

# Generate CA
openssl genrsa -out CA.key 2048
openssl req -x509 -new -batch -nodes -subj "${BASEDN}" -key CA.key -sha256 -days 3650 -out CA.crt

# Server Cert
openssl genrsa -out server.key 2048
openssl req -new -batch -key server.key -subj "${BASEDN}/CN=localhost" -out server.csr
openssl x509 -req -CA CA.crt -CAkey CA.key -CAcreateserial -days 365 -sha256 -in server.csr -extfile ../openssl.cnf -extensions SAN -out server.crt

# Client Cert
openssl genrsa -out client.key 2048
openssl req -new -batch -key client.key -subj "${BASEDN}/CN=client user" -out client.csr
openssl x509 -req -CA CA.crt -CAkey CA.key -CAcreateserial -days 365 -sha256 -in client.csr -out client.crt

# Worker cert
openssl genrsa -out worker.key 2048
openssl req -new -batch -key worker.key -subj "${BASEDN}/CN=worker" -out worker.csr
openssl x509 -req -CA CA.crt -CAkey CA.key -CAcreateserial -days 365 -sha256 -in worker.csr -out worker.crt
