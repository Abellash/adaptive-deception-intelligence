FROM nginx:alpine
COPY . /usr/share/nginx/html
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 80
