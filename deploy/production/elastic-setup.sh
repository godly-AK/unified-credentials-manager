#!/usr/bin/env bash
set -euo pipefail

cd /usr/share/elasticsearch
if [[ "${1:-}" == "certs" ]]; then
  mkdir -p config/certs

if [[ ! -f config/certs/ca/ca.crt ]]; then
  bin/elasticsearch-certutil ca --silent --pem -out config/certs/ca.zip
  unzip -q config/certs/ca.zip -d config/certs
fi

if [[ -f config/certs/ca/ca.key ]]; then
  mv config/certs/ca/ca.key /etc/ucm/ca-private/ca.key
fi

if [[ ! -f config/certs/elasticsearch/elasticsearch.crt ]]; then
  cat > config/certs/instances.yml <<'EOF'
instances:
  - name: elasticsearch
    dns:
      - elasticsearch
      - localhost
    ip:
      - 127.0.0.1
EOF
  bin/elasticsearch-certutil cert --silent --pem \
    --in config/certs/instances.yml \
    --ca-cert config/certs/ca/ca.crt \
    --ca-key /etc/ucm/ca-private/ca.key \
    --out config/certs/certs.zip
  unzip -q config/certs/certs.zip -d config/certs
fi

  rm -f config/certs/ca.zip config/certs/certs.zip config/certs/instances.yml
  chmod 700 /etc/ucm/ca-private
  chmod 600 /etc/ucm/ca-private/ca.key

  chown -R root:0 config/certs
  find config/certs -type d -exec chmod 750 {} \;
  find config/certs -type f -exec chmod 640 {} \;
  echo 'Monitoring certificates are ready.'
  exit 0
fi

if [[ "${1:-}" != "password" ]]; then
  echo 'Expected certs or password.' >&2
  exit 2
fi

if [[ ! "${UCM_KIBANA_PASSWORD}" =~ ^[A-Za-z0-9_-]{20,}$ ]]; then
  echo 'UCM_KIBANA_PASSWORD must be a 20+ character URL-safe value.' >&2
  exit 2
fi

until curl -sS --cacert config/certs/ca/ca.crt https://elasticsearch:9200 | grep -q 'missing authentication credentials'; do
  sleep 5
done

until curl -fsS --cacert config/certs/ca/ca.crt \
  -u "elastic:${UCM_ELASTIC_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -X POST https://elasticsearch:9200/_security/user/kibana_system/_password \
  -d "{\"password\":\"${UCM_KIBANA_PASSWORD}\"}" | grep -q '^{}'; do
  sleep 5
done

secret_file=/etc/ucm/monitor-secrets/exporter-api-key
if [[ ! -s "$secret_file" ]]; then
  response=$(curl -fsS --cacert config/certs/ca/ca.crt \
    -u "elastic:${UCM_ELASTIC_PASSWORD}" \
    -H 'Content-Type: application/json' \
    -X POST https://elasticsearch:9200/_security/api_key \
    -d '{"name":"ucm-audit-exporter","role_descriptors":{"ucm_events_writer":{"cluster":[],"indices":[{"names":["ucm-security-events-v1"],"privileges":["auto_configure","index"]}]}}}')
  encoded=$(printf '%s' "$response" | sed -n 's/.*"encoded":"\([^"]*\)".*/\1/p')
  if [[ ! "$encoded" =~ ^[A-Za-z0-9+/=]+$ ]]; then
    echo 'Elasticsearch did not return an encoded API key.' >&2
    exit 1
  fi
  printf '%s' "$encoded" > "$secret_file"
  chmod 640 "$secret_file"
fi
echo 'Secured monitoring certificates, Kibana account, and exporter key are ready.'
