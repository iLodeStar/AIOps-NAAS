# Java Application Integration Examples

## Spring Boot with Logback HTTP Appender

### 1. Add Dependencies (pom.xml)
```xml
<dependency>
    <groupId>ch.qos.logback</groupId>
    <artifactId>logback-classic</artifactId>
    <version>1.4.7</version>
</dependency>
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version>7.3</version>
</dependency>
```

### 2. Logback Configuration (src/main/resources/logback-spring.xml)
```xml
<configuration>
    <springProfile name="!local">
        <!-- AIOps NAAS HTTP Appender -->
        <appender name="AIOPS_HTTP" class="ch.qos.logback.core.net.SocketAppender">
            <remoteHost>application-log-collector</remoteHost>
            <port>5140</port>
            <encoder class="net.logstash.logback.encoder.LoggingEventCompositeJsonEncoder">
                <providers>
                    <timestamp/>
                    <logLevel/>
                    <loggerName/>
                    <message/>
                    <arguments/>
                    <stackTrace/>
                    <pattern>
                        <pattern>
                            {
                                "service_name": "${spring.application.name:-unknown}",
                                "application": "cruise-management",
                                "host": "${HOSTNAME:-localhost}",
                                "trace_id": "%X{traceId:-}",
                                "span_id": "%X{spanId:-}",
                                "thread": "%thread"
                            }
                        </pattern>
                    </pattern>
                </providers>
            </encoder>
        </appender>
    </springProfile>
    
    <!-- Console appender for local development -->
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>
    
    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
        <springProfile name="!local">
            <appender-ref ref="AIOPS_HTTP"/>
        </springProfile>
    </root>
</configuration>
```

### 3. Application Properties
```properties
# application-production.properties
spring.application.name=user-service
logging.level.com.cruise.userservice=DEBUG
management.tracing.enabled=true
```

### 4. Java Code Example
```java
package com.cruise.userservice;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    private static final Logger logger = LoggerFactory.getLogger(UserService.class);
    
    public User authenticateUser(String username, String password) {
        String traceId = generateTraceId();
        MDC.put("traceId", traceId);
        MDC.put("userId", username);
        
        try {
            logger.info("Authentication attempt for user: {}", username);
            
            User user = userRepository.findByUsername(username);
            if (user == null) {
                logger.warn("Authentication failed - user not found: {}", username);
                return null;
            }
            
            if (!passwordEncoder.matches(password, user.getPassword())) {
                logger.warn("Authentication failed - invalid password for user: {}", username);
                return null;
            }
            
            logger.info("Authentication successful for user: {}", username);
            return user;
            
        } catch (Exception e) {
            logger.error("Authentication error for user: {}", username, e);
            throw new AuthenticationException("Authentication failed", e);
        } finally {
            MDC.clear();
        }
    }
    
    private String generateTraceId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }
}
```

## Alternative: Direct HTTP Logging

### HTTP Appender Configuration
```java
package com.cruise.logging;

import ch.qos.logback.core.AppenderBase;
import ch.qos.logback.classic.spi.ILoggingEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public class AIOpsHttpAppender extends AppenderBase<ILoggingEvent> {
    private String url = "http://application-log-collector:8090/api/logs/single";
    private String serviceName;
    private String application;
    private HttpClient httpClient;
    private ObjectMapper objectMapper;
    
    @Override
    public void start() {
        httpClient = HttpClient.newHttpClient();
        objectMapper = new ObjectMapper();
        super.start();
    }
    
    @Override
    protected void append(ILoggingEvent event) {
        try {
            Map<String, Object> logEntry = Map.of(
                "timestamp", Instant.ofEpochMilli(event.getTimeStamp()).toString(),
                "level", event.getLevel().toString(),
                "message", event.getFormattedMessage(),
                "service_name", serviceName,
                "application", application,
                "logger_name", event.getLoggerName(),
                "thread", event.getThreadName(),
                "host", System.getenv().getOrDefault("HOSTNAME", "localhost")
            );
            
            String json = objectMapper.writeValueAsString(logEntry);
            
            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();
            
            // Async send to avoid blocking application
            CompletableFuture.supplyAsync(() -> {
                try {
                    return httpClient.send(request, HttpResponse.BodyHandlers.ofString());
                } catch (Exception e) {
                    // Log to console if HTTP logging fails
                    System.err.println("Failed to send log to AIOps: " + e.getMessage());
                    return null;
                }
            });
            
        } catch (Exception e) {
            // Don't throw exceptions from logger
            System.err.println("Error in AIOps HTTP appender: " + e.getMessage());
        }
    }
    
    // Getters and setters for configuration
    public void setUrl(String url) { this.url = url; }
    public void setServiceName(String serviceName) { this.serviceName = serviceName; }
    public void setApplication(String application) { this.application = application; }
}
```

## Docker Compose Integration

### Environment Variables
```yaml
services:
  user-service:
    image: cruise/user-service:latest
    environment:
      - SPRING_PROFILES_ACTIVE=production
      - LOGGING_APPENDER_AIOPS_HOST=application-log-collector
      - LOGGING_APPENDER_AIOPS_PORT=5140
      - SPRING_APPLICATION_NAME=user-service
    depends_on:
      - application-log-collector
    networks:
      - aiops-network
```

## Microservices Architecture Integration

### Service Mesh Integration (Istio)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aiops-logging-config
data:
  logback-spring.xml: |
    <configuration>
      <appender name="AIOPS_HTTP" class="com.cruise.logging.AIOpsHttpAppender">
        <url>http://application-log-collector.aiops.svc.cluster.local:8090/api/logs/single</url>
        <serviceName>${SPRING_APPLICATION_NAME}</serviceName>
        <application>cruise-platform</application>
      </appender>
      <root level="INFO">
        <appender-ref ref="AIOPS_HTTP"/>
      </root>
    </configuration>
```

This configuration provides production-ready Java application integration with the AIOps NAAS system for comprehensive log collection and analysis.