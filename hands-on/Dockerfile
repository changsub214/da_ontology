# Stage: Serve with Nginx Alpine
FROM nginx:alpine

# Remove default nginx configurations and html files
RUN rm -rf /etc/nginx/conf.d/* /usr/share/nginx/html/*

# Copy custom nginx configuration (configured for Cloud Run Port 8080)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy web static assets
COPY . /usr/share/nginx/html
RUN chmod -R 755 /usr/share/nginx/html

# Expose default Cloud Run port
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
