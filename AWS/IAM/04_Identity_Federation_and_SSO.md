# AWS IAM — Identity Federation & SSO

## Why Federation?

Companies with 50,000 employees can't create 50,000 IAM Users (5,000 limit + credential management nightmare). Federation = authenticate **outside** AWS, still access AWS resources. No IAM Users created.

```mermaid
flowchart LR
    IDP["External Identity Provider\n(Okta, AD FS, Google, Facebook)"] -->|"Token/Assertion"| STS["AWS STS"]
    STS -->|"Temp Credentials"| USER["User"]
    USER -->|"Access"| AWS["AWS Resources"]

    style IDP fill:#e76f51,color:#fff
    style STS fill:#2a9d8f,color:#fff
    style AWS fill:#264653,color:#fff
```

---

## The 4 Federation Mechanisms

### 1. SAML 2.0 Federation (Enterprise SSO)

```mermaid
sequenceDiagram
    participant User as Employee
    participant IdP as Corporate IdP (Okta/ADFS)
    participant AWS as AWS STS
    participant Console as AWS Console

    User->>IdP: Login (username + password + MFA)
    IdP->>IdP: Authenticate user
    IdP-->>User: SAML Assertion (signed XML)
    Note over IdP,User: "This is John, he's in Admin group"
    User->>AWS: AssumeRoleWithSAML(assertion)
    AWS->>AWS: Validate SAML signature
    AWS->>AWS: Map SAML attributes → IAM Role
    AWS-->>User: Temp credentials
    User->>Console: Access Console/CLI with temp creds
```

**Key details:**
- Used by large enterprises with existing identity infrastructure (Active Directory, Okta, OneLogin)
- IdP sends a **signed XML assertion** proving identity + group membership
- AWS maps SAML attributes → IAM Role (e.g., Admin group → AdminRole)
- **No custom code needed** — AWS Console supports SAML natively
- Max session: **12 hours**

### 2. OIDC / Web Identity Federation (Web/Mobile Apps)

```mermaid
sequenceDiagram
    participant User as Mobile/Web User
    participant Google as Google/Facebook
    participant STS as AWS STS
    participant S3 as S3 Bucket

    User->>Google: Login with Google
    Google-->>User: OIDC Token (JWT)
    User->>STS: AssumeRoleWithWebIdentity(token)
    STS->>STS: Validate JWT with Google
    STS-->>User: Temp AWS credentials
    User->>S3: Upload photo to user-specific prefix
```

**Key details:**
- For public-facing apps where users authenticate via Google, Facebook, Apple, etc.
- **AWS recommends Cognito instead of direct OIDC** — Cognito wraps this + adds features
- Direct `AssumeRoleWithWebIdentity` is supported but considered legacy pattern

### 3. AWS IAM Identity Center (Modern Standard — formerly AWS SSO)

```mermaid
flowchart TD
    subgraph IC["IAM Identity Center"]
        IS["Identity Source\n(Built-in / AD / External IdP)"]
        PS["Permission Sets\n(Templates mapped to IAM policies)"]
    end

    IS --> PS

    PS -->|"Mapped to"| DEV["Dev Account\nDevOps Permission Set"]
    PS -->|"Mapped to"| STAGING["Staging Account\nReadOnly Permission Set"]
    PS -->|"Mapped to"| PROD["Prod Account\nLimited Permission Set"]

    style IC fill:#264653,color:#fff
    style DEV fill:#2a9d8f,color:#fff
    style STAGING fill:#f4a261,color:#000
    style PROD fill:#e76f51,color:#fff
```

**Key details:**
- AWS's **built-in, recommended** SSO solution
- Centrally manage access across **all accounts** in your Organization
- Uses **Permission Sets** (templates) instead of individual roles per account
- Supports multiple identity sources: built-in store, Active Directory, external SAML/OIDC IdPs
- Provides a **user portal** — employees see all accounts they have access to
- Creates IAM Roles behind the scenes — but you manage them as Permission Sets

### 4. Custom Identity Broker (Legacy)

```
User → Your custom app → Validates against your DB → Calls STS GetFederationToken → Returns temp creds
```

- You write code to authenticate users against your own identity store
- Then call STS directly to get temp credentials
- **Avoid** — only exists for legacy systems that can't use SAML/OIDC/Cognito

---

## Cognito — The Two Pieces

```mermaid
flowchart TD
    subgraph AUTH["Authentication Layer"]
        UP["Cognito User Pool\n\n• User directory (sign-up/sign-in)\n• Returns JWT tokens\n• MFA, email verification\n• Hosted UI\n• Social login (Google, FB)\n\n→ AuthN: 'Who is this person?'"]
    end

    subgraph AUTHZ["Authorization Layer"]
        IP["Cognito Identity Pool\n\n• Exchanges JWT/social tokens\n  for AWS credentials (STS)\n• Maps to IAM Roles\n• Authenticated vs Guest roles\n\n→ AuthZ: 'Give them AWS permissions'"]
    end

    USER1["User"] -->|"Sign up / Sign in"| UP
    UP -->|"JWT Token"| IP
    USER2["Google Login"] -->|"OIDC Token"| IP
    IP -->|"STS Temp Credentials"| AWS["AWS Resources\n(S3, DynamoDB, etc.)"]

    style UP fill:#2a9d8f,color:#fff
    style IP fill:#e76f51,color:#fff
    style AWS fill:#264653,color:#fff
```

### Cognito Comparison

| | User Pool | Identity Pool |
|---|---|---|
| **Purpose** | AuthN — "Who is this person?" | AuthZ — "What AWS resources can they access?" |
| **Returns** | JWT tokens (ID, Access, Refresh) | AWS temp credentials (AccessKey + SecretKey + SessionToken) |
| **Features** | Sign-up/sign-in, MFA, email verify, hosted UI, social login | Maps tokens → IAM Roles, supports authenticated + guest access |
| **Used for** | Your app's user management | Granting actual AWS API access to end users |
| **Can work alone?** | ✅ (just for app auth, no AWS access) | ✅ (accepts social tokens without User Pool) |

> **SDE2 Trap:** User Pools and Identity Pools solve **different problems**. User Pools = identity management. Identity Pools = AWS credential vending. You often use both together, but they're independent services.

---

## Federation Decision Matrix

| Scenario | Mechanism | Why |
|----------|----------|-----|
| Enterprise with Okta/AD FS, employees need AWS Console | **SAML 2.0** or **IAM Identity Center** | Standard enterprise SSO protocol |
| Multi-account org, centralized access management | **IAM Identity Center** | Built for this. Permission Sets across accounts. |
| Mobile app, users log in with Google/Facebook | **Cognito (User Pool + Identity Pool)** | Managed user directory + AWS credential vending |
| Web app, users upload to user-specific S3 prefix | **Cognito Identity Pool** | Maps authenticated user → scoped IAM Role |
| Legacy system with custom auth DB | **Custom Identity Broker** | Last resort. Calls STS directly. |

---

## Real-World Example — Mobile App with Cognito

```mermaid
sequenceDiagram
    participant User as Mobile User
    participant App as Mobile App
    participant CUP as Cognito User Pool
    participant CIP as Cognito Identity Pool
    participant S3 as S3

    User->>App: Sign in (email + password)
    App->>CUP: Authenticate
    CUP-->>App: JWT tokens (ID + Access + Refresh)

    App->>CIP: Exchange JWT for AWS creds
    CIP->>CIP: Map to IAM Role (AuthenticatedRole)
    CIP-->>App: Temp AWS credentials

    Note over App,S3: IAM Role policy restricts to user-specific S3 prefix
    App->>S3: PutObject s3://photos/${cognito-identity.sub}/photo.jpg
    S3-->>App: Success

    Note over S3: Policy uses ${cognito-identity.amazonaws.com:sub}
    Note over S3: as variable → each user can only access their own prefix
```

**IAM policy for per-user S3 access:**
```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::photo-bucket/${cognito-identity.amazonaws.com:sub}/*"
}
```

---

## ⚠️ Gotchas & Edge Cases

| Gotcha | Detail |
|--------|--------|
| **SAML ≠ OIDC** | SAML = XML-based, enterprise, older. OIDC = JSON/JWT-based, modern, web-friendly. Don't conflate. |
| **Cognito User Pools ≠ AWS credentials** | User Pools give JWTs for your app. Only Identity Pools give STS credentials for AWS access. |
| **IAM Identity Center = AWS SSO renamed** | Same service, new name. Interviewers may use either. |
| **Federation session limits** | SAML = 12 hrs max. Web Identity = 1 hr default (extendable via Cognito). |
| **Cognito has region limits** | User Pools are regional. For global apps, consider Cognito in multiple regions or use a global IdP. |
| **Token refresh** | Cognito Refresh Token = 30 days default (configurable 1 day → 10 years). Access/ID tokens = 1 hour, not configurable. |
| **Identity Pool guest access** | Identity Pools can issue credentials to unauthenticated users — useful but risky if role is too permissive. |

---

## 📌 Interview Cheat Sheet

- 50,000 employees → **Federation**, not 50,000 IAM Users
- Enterprise SSO → **SAML 2.0** or **IAM Identity Center**
- Multi-account centralized access → **IAM Identity Center** (recommended)
- Mobile/web public users → **Cognito** (User Pool + Identity Pool)
- Cognito User Pool = JWT tokens (**AuthN**). Identity Pool = AWS credentials (**AuthZ**).
- **IAM Identity Center** = recommended multi-account SSO for Organizations
- Custom Identity Broker = legacy, avoid unless forced
- Per-user S3 access → Cognito Identity Pool + policy variable `${cognito-identity.amazonaws.com:sub}`
- SAML = XML, enterprise. OIDC = JWT, modern web. Different protocols.
- Permission Sets (Identity Center) = templates mapped to IAM policies across accounts
