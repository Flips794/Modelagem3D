# Estágios: build (compila dist/), dev (vite preview, usado pelo docker-compose.yml)
# e prod (Caddy servindo dist/ e encaminhando /api/* ao backend). Sem --target: prod.
FROM node:24-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Relativa por padrão: interface e API no mesmo domínio, atrás do Caddy.
# O docker-compose.yml de desenvolvimento passa http://127.0.0.1:8000/api/v1.
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM build AS dev
EXPOSE 5173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]

FROM caddy:2 AS prod
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80 443
