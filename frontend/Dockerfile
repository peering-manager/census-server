FROM nginx:1

COPY index.html /usr/share/nginx/html
COPY img /usr/share/nginx/html/img

COPY ./nginx.conf /etc/nginx/conf.d/default.conf
COPY ./nginx-backend-not-found.conf /etc/nginx/extra-conf.d/backend-not-found.conf
