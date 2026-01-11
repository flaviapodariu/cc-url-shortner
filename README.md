# URL Shortner App

Aplicatia contine urmatoarele componente: 

* Microserviciu autentificare
* Microserviciu pentru business logic
* Frontend / Web App (http://localhost:30003/)
* Baza de date PostgreSQL
* Adminer
* Monitorizare prin Grafana (http://localhost:30005/) + Prometheus
* Portainer (http://localhost:30004/)

Fiecare componenta are un folder separat in care se gasesc fisierele yaml pentru service-uri si deployment-uri

## Rulare
Din root folder se ruleaza urmatoarele:

`docker pull kindest/node:v1.34.0`

`kind create cluster --config ./cluster/kind-config.yaml`

Kind nu ofera Metrics API by default, asa ca trebuie adaugat manual pentru ca mecanismul de auto scaling sa functioneze:

`kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml`

In plus, trebuie facut si un patch ca sa functioneze impreuna cu Kind:

`kubectl patch deployment metrics-server -n kube-system --type 'json' -p '[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'`

`helm install dev ./helm/url-shortner-app/`

Pentru a accesa adminer, trebuie facut port-forward: 

`kubectl port-forward service/adminer-dev 8081:8081`
