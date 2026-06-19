FROM node:18-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY public/ ./public/
COPY src/ ./src/
ARG REACT_APP_COGNITO_POOL_ID
ARG REACT_APP_COGNITO_CLIENT_ID
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
