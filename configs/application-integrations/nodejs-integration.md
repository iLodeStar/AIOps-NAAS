# Node.js Application Integration Examples

## Express.js with Winston HTTP Transport

### 1. Install Dependencies
```bash
npm install winston winston-http express express-request-id
npm install --save-dev @types/winston  # For TypeScript projects
```

### 2. Winston Configuration
```javascript
// config/logger.js
const winston = require('winston');
const os = require('os');

// Custom format for AIOps NAAS
const aiopsPformat = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json(),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    return JSON.stringify({
      timestamp,
      level: level.toUpperCase(),
      message,
      service_name: process.env.SERVICE_NAME || 'nodejs-service',
      application: process.env.APPLICATION_NAME || 'cruise-platform',
      host: process.env.HOSTNAME || os.hostname(),
      trace_id: meta.traceId || meta.trace_id,
      span_id: meta.spanId || meta.span_id,
      metadata: {
        pid: process.pid,
        environment: process.env.NODE_ENV || 'development',
        ...meta
      }
    });
  })
);

// Create logger with multiple transports
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: aiopsPformat,
  defaultMeta: {
    service: process.env.SERVICE_NAME || 'nodejs-service'
  },
  transports: [
    // Console transport for local development
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    }),
    
    // HTTP transport for AIOps NAAS (production only)
    ...(process.env.NODE_ENV === 'production' ? [
      new winston.transports.Http({
        host: process.env.AIOPS_HOST || 'application-log-collector',
        port: process.env.AIOPS_PORT || 8090,
        path: '/api/logs/single',
        format: winston.format.json()
      })
    ] : []),
    
    // TCP transport alternative
    ...(process.env.AIOPS_TCP_HOST ? [
      new winston.transports.Stream({
        stream: require('net').createConnection({
          host: process.env.AIOPS_TCP_HOST,
          port: process.env.AIOPS_TCP_PORT || 5140
        }),
        format: winston.format.combine(
          winston.format.json(),
          winston.format.printf(info => JSON.stringify(info) + '\n')
        )
      })
    ] : [])
  ],
  
  // Handle transport errors gracefully
  exceptionHandlers: [
    new winston.transports.Console()
  ],
  rejectionHandlers: [
    new winston.transports.Console()
  ]
});

module.exports = logger;
```

### 3. Express.js Middleware Setup
```javascript
// middleware/logging.js
const logger = require('../config/logger');
const { v4: uuidv4 } = require('uuid');

// Request ID middleware
function requestIdMiddleware(req, res, next) {
  req.id = req.headers['x-request-id'] || uuidv4();
  res.setHeader('X-Request-ID', req.id);
  next();
}

// Logging middleware
function loggingMiddleware(req, res, next) {
  const start = Date.now();
  
  // Add request context to logger
  req.logger = logger.child({
    trace_id: req.id,
    request_id: req.id,
    method: req.method,
    url: req.url,
    user_agent: req.headers['user-agent'],
    ip: req.ip
  });
  
  // Log request start
  req.logger.info('Request started', {
    method: req.method,
    url: req.url,
    headers: req.headers
  });
  
  // Override res.end to log response
  const originalEnd = res.end;
  res.end = function(...args) {
    const duration = Date.now() - start;
    
    req.logger.info('Request completed', {
      status_code: res.statusCode,
      duration_ms: duration,
      content_length: res.get('content-length')
    });
    
    originalEnd.apply(this, args);
  };
  
  next();
}

// Error logging middleware
function errorLoggingMiddleware(err, req, res, next) {
  req.logger.error('Request error', {
    error: err.message,
    stack: err.stack,
    status_code: err.status || 500
  });
  
  next(err);
}

module.exports = {
  requestIdMiddleware,
  loggingMiddleware,
  errorLoggingMiddleware
};
```

### 4. Express.js Application
```javascript
// app.js
const express = require('express');
const logger = require('./config/logger');
const { 
  requestIdMiddleware, 
  loggingMiddleware, 
  errorLoggingMiddleware 
} = require('./middleware/logging');

const app = express();

// Middleware setup
app.use(express.json());
app.use(requestIdMiddleware);
app.use(loggingMiddleware);

// Routes
app.get('/health', (req, res) => {
  req.logger.debug('Health check requested');
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.post('/api/users', async (req, res) => {
  try {
    req.logger.info('Creating user', { user_data: req.body });
    
    // Simulate user creation
    const user = await createUser(req.body);
    
    req.logger.info('User created successfully', { 
      user_id: user.id,
      username: user.username 
    });
    
    res.status(201).json(user);
    
  } catch (error) {
    req.logger.error('Failed to create user', {
      error: error.message,
      user_data: req.body
    });
    
    res.status(500).json({ error: 'User creation failed' });
  }
});

app.get('/api/users/:id', async (req, res) => {
  const userId = req.params.id;
  
  req.logger.info('Fetching user', { user_id: userId });
  
  try {
    const user = await getUserById(userId);
    
    if (!user) {
      req.logger.warn('User not found', { user_id: userId });
      return res.status(404).json({ error: 'User not found' });
    }
    
    req.logger.info('User fetched successfully', { user_id: userId });
    res.json(user);
    
  } catch (error) {
    req.logger.error('Failed to fetch user', {
      user_id: userId,
      error: error.message
    });
    
    res.status(500).json({ error: 'Failed to fetch user' });
  }
});

// Error handling
app.use(errorLoggingMiddleware);
app.use((err, req, res, next) => {
  res.status(err.status || 500).json({
    error: process.env.NODE_ENV === 'production' ? 'Internal Server Error' : err.message
  });
});

// Start server
const port = process.env.PORT || 3000;
app.listen(port, () => {
  logger.info('Server started', { 
    port,
    environment: process.env.NODE_ENV,
    service: process.env.SERVICE_NAME
  });
});

module.exports = app;
```

### 5. Service Layer with Logging
```javascript
// services/userService.js
const logger = require('../config/logger');

class UserService {
  constructor() {
    this.logger = logger.child({ component: 'UserService' });
  }
  
  async createUser(userData, traceId) {
    const contextLogger = this.logger.child({ trace_id: traceId });
    
    try {
      contextLogger.info('Starting user creation', { 
        username: userData.username,
        email: userData.email 
      });
      
      // Validate user data
      this.validateUserData(userData, contextLogger);
      
      // Check if user exists
      const existingUser = await this.findUserByEmail(userData.email);
      if (existingUser) {
        contextLogger.warn('User already exists', { email: userData.email });
        throw new Error('User already exists');
      }
      
      // Create user in database
      const user = await this.database.users.create(userData);
      
      contextLogger.info('User created in database', { 
        user_id: user.id,
        username: user.username 
      });
      
      // Send welcome email
      await this.sendWelcomeEmail(user, contextLogger);
      
      return user;
      
    } catch (error) {
      contextLogger.error('User creation failed', {
        error: error.message,
        username: userData.username
      });
      throw error;
    }
  }
  
  validateUserData(userData, logger) {
    const errors = [];
    
    if (!userData.username) errors.push('Username required');
    if (!userData.email) errors.push('Email required');
    if (!userData.password) errors.push('Password required');
    
    if (errors.length > 0) {
      logger.warn('User validation failed', { 
        errors,
        provided_fields: Object.keys(userData)
      });
      throw new Error(`Validation failed: ${errors.join(', ')}`);
    }
    
    logger.debug('User validation passed');
  }
  
  async sendWelcomeEmail(user, logger) {
    try {
      logger.info('Sending welcome email', { 
        user_id: user.id,
        email: user.email 
      });
      
      // Email sending logic here
      await this.emailService.send({
        to: user.email,
        template: 'welcome',
        data: { username: user.username }
      });
      
      logger.info('Welcome email sent successfully', { user_id: user.id });
      
    } catch (error) {
      logger.error('Failed to send welcome email', {
        user_id: user.id,
        email: user.email,
        error: error.message
      });
      // Don't throw - email failure shouldn't fail user creation
    }
  }
}

module.exports = UserService;
```

## TypeScript Configuration

### 6. TypeScript Logger Interface
```typescript
// types/logger.ts
export interface LogContext {
  trace_id?: string;
  span_id?: string;
  user_id?: string;
  request_id?: string;
  [key: string]: any;
}

export interface Logger {
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string, context?: LogContext): void;
  debug(message: string, context?: LogContext): void;
  child(context: LogContext): Logger;
}
```

### 7. TypeScript Service Example
```typescript
// services/PaymentService.ts
import { Logger } from '../types/logger';
import logger from '../config/logger';

export class PaymentService {
  private logger: Logger;
  
  constructor() {
    this.logger = logger.child({ component: 'PaymentService' });
  }
  
  async processPayment(
    paymentData: PaymentRequest, 
    traceId: string
  ): Promise<PaymentResult> {
    const contextLogger = this.logger.child({ 
      trace_id: traceId,
      payment_id: paymentData.id,
      amount: paymentData.amount,
      currency: paymentData.currency
    });
    
    try {
      contextLogger.info('Processing payment', {
        merchant_id: paymentData.merchantId,
        payment_method: paymentData.method
      });
      
      // Validate payment
      await this.validatePayment(paymentData, contextLogger);
      
      // Process with payment gateway
      const result = await this.callPaymentGateway(paymentData, contextLogger);
      
      contextLogger.info('Payment processed successfully', {
        transaction_id: result.transactionId,
        status: result.status
      });
      
      return result;
      
    } catch (error) {
      contextLogger.error('Payment processing failed', {
        error: error.message,
        error_code: error.code
      });
      throw error;
    }
  }
}
```

## Docker Configuration

### 8. Docker Compose Service
```yaml
# docker-compose.yml
services:
  nodejs-api:
    image: cruise/nodejs-api:latest
    environment:
      - NODE_ENV=production
      - SERVICE_NAME=api-gateway
      - APPLICATION_NAME=cruise-platform
      - AIOPS_HOST=application-log-collector
      - AIOPS_PORT=8090
      - LOG_LEVEL=info
    depends_on:
      - application-log-collector
    networks:
      - aiops-network
```

### 9. Package.json Scripts
```json
{
  "scripts": {
    "start": "node app.js",
    "start:prod": "NODE_ENV=production node app.js",
    "start:aiops": "NODE_ENV=production AIOPS_HOST=application-log-collector node app.js",
    "dev": "NODE_ENV=development nodemon app.js",
    "test": "npm run test:unit && npm run test:integration",
    "test:unit": "jest --testPathPattern=test/unit",
    "test:integration": "jest --testPathPattern=test/integration"
  },
  "dependencies": {
    "express": "^4.18.2",
    "winston": "^3.8.2",
    "winston-http": "^2.0.0",
    "uuid": "^9.0.0"
  }
}
```

This configuration provides comprehensive Node.js application integration with structured logging, trace correlation, and seamless integration with the AIOps NAAS system.