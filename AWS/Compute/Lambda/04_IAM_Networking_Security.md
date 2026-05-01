# AWS Lambda — IAM, Networking & Security

## Two Sides of Lambda IAM

Lambda has **two completely separate** IAM mechanisms. Most people conflate them.

```mermaid
flowchart LR
    subgraph INBOUND["WHO can invoke Lambda?"]
        S3["S3"]
        APIGW["API Gateway"]
        SNS["SNS"]
        ACCB["Account B"]
    end
    subgraph LAMBDA["Lambda Function"]
        RP["Resource Policy\n(gates entry)"]
        ER["Execution Role\n(gates exit)"]
    end
    subgraph OUTBOUND["WHAT can Lambda do?"]
        S3O["S3"]
        DDB["DynamoDB"]
        SQS["SQS"]
    end

    S3 --> RP
    APIGW --> RP
    SNS --> RP
    ACCB --> RP
    ER --> S3O
    ER --> DDB
    ER --> SQS

    style INBOUND fill:#264653,color:#fff
    style LAMBDA fill:#e76f51,color:#fff
    style OUTBOUND fill:#2d6a4f,color:#fff
```

### Execution Role (What Lambda CAN DO)

IAM role Lambda **assumes** at INIT. Defines which AWS services your function can talk to.

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "dynamodb:PutItem", "sqs:SendMessage"],
  "Resource": "arn:aws:s3:::my-bucket/*"
}
```

- Every Lambda **must** have an execution role
- Lambda calls `sts:AssumeRole` → temporary creds injected as env vars
- SDK clients auto-discover these — why `boto3.client('s3')` works without explicit credentials

### Resource Policy (Who Can INVOKE Lambda)

Policy attached to the Lambda function itself. Controls who/what can call it.

```json
{
  "Effect": "Allow",
  "Principal": { "Service": "s3.amazonaws.com" },
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:us-east-1:123456:function:my-func",
  "Condition": { "ArnLike": { "AWS:SourceArn": "arn:aws:s3:::my-bucket" } }
}
```

- Without this, trigger services get `AccessDeniedException`
- SAM/CDK add these automatically when you define event sources

---

## Cross-Account Invocation

> **[SDE2 TRAP]** "Can Lambda in Account A invoke Lambda in Account B?" — Yes, but you need **BOTH doors open:**

```mermaid
flowchart LR
    subgraph ACCA["Account A (Caller)"]
        ROLE_A["Execution Role:\nlambda:InvokeFunction\non Account B's ARN"]
    end
    subgraph ACCB["Account B (Target)"]
        RP_B["Resource Policy:\nPrincipal = Account A's role ARN\nAction = lambda:InvokeFunction"]
    end

    ROLE_A -->|"Both must allow"| RP_B

    style ACCA fill:#1a535c,color:#fff
    style ACCB fill:#6a0572,color:#fff
```

> Scope principal to **specific role ARN**, not entire account. `"AWS": "arn:aws:iam::ACCOUNT_A:root"` allows ANY role in Account A — too broad.

---

## Least Privilege — Production Standard

```json
// 🐛 TERRIBLE — "just make it work"
{ "Effect": "Allow", "Action": "s3:*", "Resource": "*" }

// ✅ PRODUCTION — scoped to exact actions and resources
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::papers-bucket/raw/*"
}
```

**Checklist:**
- Scope **actions** to exact API calls (not `s3:*`)
- Scope **resources** to exact ARNs (not `*`)
- Use **conditions** where possible (`aws:SourceAccount`, `s3:prefix`)
- **Separate roles per function** — download function shouldn't have DynamoDB write access

---

## Lambda in a VPC — When and Why

### Default vs VPC Mode

| | Default (No VPC) | In Your VPC |
|--|-----------------|-------------|
| Internet access | ✅ Yes | ❌ Lost |
| AWS API access (S3, DDB) | ✅ Yes | ❌ Lost |
| Private resources (RDS) | ❌ No | ✅ Yes |
| Complexity | Low | Higher |

> **Only put Lambda in VPC when accessing private resources** (RDS, ElastiCache, OpenSearch). Every unnecessary VPC Lambda = added complexity + NAT cost.

### Restoring Connectivity from VPC

```mermaid
flowchart TD
    subgraph VPC["YOUR VPC"]
        subgraph PRIV["Private Subnet"]
            LAMBDA["Lambda (ENI)"]
        end
        RDS["RDS ✅ Direct"]
        GW_EP["Gateway VPC Endpoint\n(S3, DynamoDB)\n✅ FREE"]
        IF_EP["Interface VPC Endpoint\n(SQS, Secrets Mgr)\n✅ Private, ~$7/mo/AZ"]
        NAT["NAT Gateway\n(Internet access)\n💰 ~$32/mo/AZ"]
    end

    LAMBDA --> RDS
    LAMBDA --> GW_EP
    LAMBDA --> IF_EP
    LAMBDA --> NAT
    NAT --> IGW["IGW"] --> INET["Internet\n(External APIs)"]

    style LAMBDA fill:#2a9d8f,color:#fff
    style RDS fill:#264653,color:#fff
    style GW_EP fill:#2d6a4f,color:#fff
    style IF_EP fill:#e76f51,color:#fff
    style NAT fill:#d00000,color:#fff
```

| Target | Solution | Cost |
|--------|----------|------|
| S3, DynamoDB | **Gateway VPC Endpoint** | **Free** |
| SQS, Secrets Manager, SSM | **Interface VPC Endpoint (PrivateLink)** | ~$7/mo per endpoint per AZ |
| External APIs (Stripe, GitHub) | **NAT Gateway** | ~$32/mo per AZ + data processing |

---

## ENIs and Cold Start History

| Era | Behavior | Cold Start Penalty |
|-----|----------|-------------------|
| **Pre-2019** | New ENI created per environment | **10-30 seconds** |
| **Post-2019 (Hyperplane)** | Shared ENI pool managed by AWS | **~200-500ms** |

> **[SDE2 TRAP]** "VPC Lambda cold starts are terrible" — WAS true pre-2019. Post-Hyperplane, VPC adds ~200-500ms, not 10-30s. But DO mention subnet IP capacity needs.

### Subnet IP Planning

Each Lambda environment consumes **one IP** from the subnet.

```
1,000 concurrent Lambdas = 1,000 IPs needed
/24 subnet = 251 usable IPs → NOT ENOUGH
/20 subnet = 4,091 usable IPs → Safe
```

Always configure Lambda with subnets in **at least 2 AZs** for HA.

---

## Debugging Rule — Error vs Timeout

```mermaid
flowchart TD
    SYMPTOM{"What happened?"}
    SYMPTOM -->|"Instant error message\n'AccessDeniedException'"| IAM["🔑 IAM PROBLEM\nCheck execution role\nCheck resource policy"]
    SYMPTOM -->|"Hangs for 60s\nthen times out"| NET["🌐 NETWORK PROBLEM\nNo route to service\nMissing VPC Endpoint\nMissing NAT Gateway"]

    style IAM fill:#e76f51,color:#fff
    style NET fill:#264653,color:#fff
```

> ⚠️ **Memorize this.** "Access Denied" = IAM. "Timeout/Hang" = Network. Solves 80% of VPC Lambda issues.

---

## ⚠️ Gotchas & Edge Cases

1. **Security Groups on Lambda.** Yes, VPC Lambda gets SGs. Missing outbound rule = **silent timeout**, no error message.
2. **ENI limits per account.** Default ~5,000 per region. Lambda shares this with EC2, ECS. High-concurrency Lambda can exhaust quota.
3. **Multi-AZ required.** Always configure subnets in ≥2 AZs. If one AZ fails, Lambda needs alternatives.
4. **VPC Endpoint policies.** Gateway endpoints for S3 support resource policies — restrict Lambda to specific buckets beyond execution role. Defense in depth.
5. **Subnet IP exhaustion.** `/24` = 251 usable IPs. High-concurrency Lambda needs `/20` or larger.

---

## 📌 Interview Cheat Sheet

- **Execution Role** = what Lambda can do (outbound permissions)
- **Resource Policy** = who can invoke Lambda (inbound permissions)
- Cross-account needs **both** — execution role on caller + resource policy on target
- Default Lambda has internet. **VPC Lambda loses it** — restore with NAT GW or VPC Endpoints
- **Gateway Endpoints** (S3, DynamoDB) = free. **Interface Endpoints** = ~$7/mo/AZ
- Post-2019 Hyperplane: VPC cold start penalty is **~200-500ms**, not 10-30s
- Put Lambda in VPC **only** when accessing private resources
- Subnet sizing: plan for **peak concurrent executions = IPs needed**
- Debugging: error message = IAM problem, timeout = network problem
