FROM nginxinc/nginx-unprivileged:stable-alpine

# nginx renders this template at startup, filling in API_UPSTREAM.
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY public/ /usr/share/nginx/html/

# Default for local Docker. Kubernetes overrides it with the api Service.
ENV API_UPSTREAM=http://host.docker.internal:8001

USER 101

EXPOSE 8080
