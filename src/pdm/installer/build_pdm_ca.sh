#!/bin/bash

# Stop on any kind of error
set -e

# Generate a CA, arguments:
# base_dir, ca_dn, ca_days, ca_keylen, ca_signdn
function gen_ca
{
  BASE_DIR=$1
  CA_DN=$2
  CA_DAYS=$3
  CA_KEYLEN=$4
  CA_SIGNDN=$5
  # Generate the certs
  CA_KEY_PATH="${BASE_DIR}/ca_key.pem"
  openssl genrsa -out "${CA_KEY_PATH}" ${CA_KEYLEN}
  openssl req -x509 -new -batch -nodes \
              -subj "${CA_DN}" \
              -key "${CA_KEY_PATH}" \
              -sha256 -days ${CA_DAYS} \
              -set_serial 01 \
              -out "${BASE_DIR}/ca_crt.pem"
  # Create extra files
  echo "01" > "${BASE_DIR}/serial"
  cat > "${BASE_DIR}/ca_crt.signing_policy" << EOF
access_id_CA   X509    '${CA_DN}'
pos_rights     globus  CA:sign
cond_subjects  globus  '"${CA_SIGNDN}/*"'
EOF
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
              -subj "/O=${CERT_HOST}/OU=Hosts/CN=${CERT_HOST}" \
              -out "${HOSTREQ}"
  # Now sign the request
  CA_CERT="${BASE_DIR}/ca_crt.pem"
  CA_KEY="${BASE_DIR}/ca_key.pem"
  CA_CONF="${BASE_DIR}/openssl.cnf"
  SAN="${CERT_HOST}" openssl x509 -req -CA "${CA_CERT}" -CAkey "${CA_KEY}" \
               -CAserial "${BASE_DIR}/serial" -days $CERT_DAYS -sha256 \
               -in "${HOSTREQ}" -extfile "${CA_CONF}" -extensions SAN \
               -out "${HOSTCERT}"
  # MyProxy is fussy about key permissions, even if directory protects files
  chmod 600 "${HOSTKEY}"
  return
}

# Add a CA hash to a hash dir:
# hash_dir, ca_base_dir
function add_to_hashdir
{
  HASH_DIR=$1
  CA_DIR=$2
  CA_HASH=`openssl x509 -in "${CA_DIR}/ca_crt.pem" -noout -hash`
  ln -s "${CA_DIR}/ca_crt.pem" "${HASH_DIR}/${CA_HASH}.0"
  ln -s "${CA_DIR}/ca_crt.signing_policy" "${HASH_DIR}/${CA_HASH}.signing_policy"
  return
}


if [ "$#" -ne "2" ]; then
  echo "Usage: $0 <dir> <hostname>"
  exit 1
fi

# Create the directory if it doesn't exist
mkdir -p "${1}"
TARGET_DIR="`realpath "${1}"`"
MY_HOST=$2
CA_DAYS=3650
CA_KEYLEN=2048
HOST_DAYS=1825
HOST_KEYLEN=2048
HOST_CA_PATH="${TARGET_DIR}/host"
HOST_CA_DN="/O=${MY_HOST}/CN=Host CA"
HOST_CA_SIGNDN="/O=${MY_HOST}/OU=Hosts"
USER_CA_PATH="${TARGET_DIR}/user"
USER_CA_DN="/O=${MY_HOST}/CN=User CA"
USER_CA_SIGNDN="/O=${MY_HOST}/OU=Users"

if [ -d "${HOST_CA_PATH}" ]; then
  echo "Target dir (${TARGET_DIR}) already contains a CA. Exiting." >&2
  exit 1
fi

# Create basic directory and configs
mkdir -p "${HOST_CA_PATH}" "${USER_CA_PATH}"
chmod 700 "${HOST_CA_PATH}" "${USER_CA_PATH}"
cat > "${HOST_CA_PATH}/openssl.cnf" << EOF
[ SAN ]
subjectAltName=DNS:\${ENV::SAN}
EOF
cat > "${USER_CA_PATH}/mapper" << EOF
#!/bin/sh

if [ "\$#" -ne 1 -o -z "\${1}" ]; then
  exit 1
fi
echo "${USER_CA_SIGNDN}/CN=\${1}"
exit 0
EOF
chmod +x "${USER_CA_PATH}/mapper"

# Generate CA certificates
gen_ca "${HOST_CA_PATH}" "${HOST_CA_DN}" ${CA_DAYS} ${CA_KEYLEN} "${HOST_CA_SIGNDN}"
gen_ca "${USER_CA_PATH}" "${USER_CA_DN}" ${CA_DAYS} ${CA_KEYLEN} "${USER_CA_SIGNDN}"

# Generate a hostcert for this node
gen_hostcert "${HOST_CA_PATH}" "${MY_HOST}" ${HOST_DAYS} ${HOST_KEYLEN}

# Now generate the certificate hash dir
HASH_DIR="${TARGET_DIR}/certificates"
mkdir "${HASH_DIR}"
add_to_hashdir "${HASH_DIR}" "${USER_CA_PATH}"
add_to_hashdir "${HASH_DIR}" "${HOST_CA_PATH}"

