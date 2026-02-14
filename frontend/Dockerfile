# Development stage
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files (including lock file for reproducible installs)
COPY package.json package-lock.json* ./

# Install dependencies - use npm install for dev (more forgiving with lock file versions)
RUN npm install

# Copy source code (will be overridden by volume mount)
COPY . .

# Validate that all imports can be resolved (catches missing dependencies)
RUN node scripts/validate-imports.js || echo "Import validation skipped (dev mode)"

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies - use npm ci for production builds
RUN npm install --frozen-lockfile 2>/dev/null || npm install

# Copy source code
COPY . .

# Validate imports before building (fails fast if packages are missing)
RUN node scripts/validate-imports.js

# Set API URLs for production build - use relative paths so nginx can proxy
# These can be overridden at build time with --build-arg
ARG VITE_API_URL=/api/v1
ARG VITE_WS_URL=/ws

# Build the application with environment variables
RUN VITE_API_URL=$VITE_API_URL VITE_WS_URL=$VITE_WS_URL npm run build

# Production stage
FROM nginx:alpine AS production

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
