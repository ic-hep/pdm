#!/bin/bash

# Generate a CA, arguments:
# base_dir, ca_dn, ca_days, ca_keylen
function gen_ca
{
  BASE_DIR=$1
  CA_DN=$2
  CA_DAYS=$3
  CA_KEYLEN=$4
  # Generate the certs
  CA_KEY_PATH="${BASE_DIR}/ca_key.pem"
  openssl genrsa -out "${CA_KEY_PATH}" ${CA_KEYLEN}
  openssl req -x509 -new -batch -nodes \
              -subj "${CA_DN}" \
              -key "${CA_KEY_PATH}" \
              -sha256 -days ${CA_DAYS} \
              -out "${BASE_DIR}/ca_crt.pem"
  # Create template dirs
  mkdir -p "${BASE_DIR}/reqs" "${BASE_DIR}/certs" "${BASE_DIR}/keys"
  return
}

# Generate a host cert, arguments:
# base_dir, hostname, cert_days, cert_keylen
function gen_hostcert
{
  BASE_DIR=$1
  CERT_HOST=$2
  CERT_DAYS=$3
  CERT_KEYLEN=$4
  HOSTREQ="${BASE_DIR}/reqs/${CERT_HOST}.csr"
  HOSTCERT="${BASE_DIR}/certs/${CERT_HOST}.crt"
  HOSTKEY="${BASE_DIR}/keys/${CERT_HOST}.key"
  # Generate a key and request
  openssl genrsa -out "${HOSTKEY}" $CERT_KEYLEN
  openssl req -new -batch -key "${HOSTKEY}" \
              -subj "/OU=Hosts/CN=${CERT_HOST}" -out "${HOSTREQ}"
  # Now sign the request
  CA_CERT="${BASE_DIR}/ca_crt.pem"
  CA_KEY="${BASE_DIR}/ca_key.pem"
  CA_CONF="${BASE_DIR}/openssl.cnf"
  SAN="${CERT_HOST}" openssl x509 -req -CA "${CA_CERT}" -CAkey "${CA_KEY}" \
               -CAcreateserial -days $CERT_DAYS -sha256 -in "${HOSTREQ}" \
               -extfile "${CA_CONF}" -extensions SAN -out "${HOSTCERT}"
  return
}

if [ "$#" -ne "2" ]; then
  echo "Usage: $0 <dir> <hostname>"
  exit 1
fi

TARGET_DIR=$1
MY_HOST=$2
CA_DAYS=3650
CA_KEYLEN=2048
HOST_DAYS=1825
HOST_KEYLEN=2048
HOST_CA_PATH="${TARGET_DIR}/host"
HOST_CA_DN="/CN=${MY_HOST} Host CA"
USER_CA_PATH="${TARGET_DIR}/user"
USER_CA_DN="/CN=${MY_HOST} User CA"

if [ -d "${TARGET_DIR}" ]; then
  echo "Target dir (${TARGET_DIR}) already exists. Exiting."
  exit 1
fi

# Create basic directory and configs
mkdir -p "${HOST_CA_PATH}" "${USER_CA_PATH}"
cat > "${HOST_CA_PATH}/openssl.cnf" << EOF
[ SAN ]
subjectAltName=DNS:\${ENV::SAN}
EOF

# Generate CA certificates
gen_ca "${HOST_CA_PATH}" "${HOST_CA_DN}" ${CA_DAYS} ${CA_KEYLEN}
gen_ca "${USER_CA_PATH}" "${USER_CA_DN}" ${CA_DAYS} ${CA_KEYLEN}

# Generate a hostcert for this node
gen_hostcert "${HOST_CA_PATH}" "${MY_HOST}" ${HOST_DAYS} ${HOST_KEYLEN}

