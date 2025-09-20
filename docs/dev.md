# Development Guidelines

This document outlines best practices for contributing to the **Booster Bookstore Chatbot**. Following these guidelines ensures consistent, maintainable, and production-ready code across all services.

---

## 🔀 Branching Strategy

We use a **feature-driven Git workflow** based on short-lived branches. The goal is to keep `main` always deployable and make changes in a structured, trackable way.

### Branch Types

-   **`main`**

    -   Always **stable** and **deployable**.
    -   Contains code that has passed testing and review.
    -   Direct commits are not allowed.

-   **`dev`**

    -   Integration branch for features.
    -   Code must pass CI checks before merging.
    -   Regularly rebased/merged into `main` after release testing.

-   **`feature/<name>`**

    -   Used for new functionality, improvements, or experiments.
    -   Branch off `dev`.
    -   Use clear names:
        -   `feature/chat-intents-parser`
        -   `feature/user-auth-middleware`

-   **`bugfix/<ticket>`**

    -   For fixing bugs discovered during development.
    -   Branch off `dev`.
    -   Example: `bugfix/response-delay-123`

-   **`hotfix/<ticket>`**
    -   For urgent fixes in **production**.
    -   Branch off `main`, then merged back into both `main` and `dev`.
    -   Example: `hotfix/db-connection-issue`

### Workflow

1. **Start a new branch**

    ```bash
    git checkout dev
    git pull origin dev
    git checkout -b feature/<name>
    ```

2. **Work locally**

    - Keep commits small and descriptive.
    - Use [Conventional Commits](https://www.conventionalcommits.org/):
        - `feat: add new user session handler`
        - `fix: resolve null pointer in chatbot response`

3. **Sync often**

    - Rebase or merge `dev` regularly to stay up-to-date.
    - Avoid long-lived branches.

4. **Open a PR**

    - Target branch: `dev` (unless it’s a `hotfix`).
    - Request at least one reviewer.
    - Ensure CI tests pass.

5. **Merge strategy**
    - Squash commits to keep history clean.
    - Delete branch after merging.

---

## 🧪 Code Quality & Testing

-   Write **unit tests** for every microservice.
-   Run `docker-compose up --build` before pushing to confirm integration across services.
-   CI/CD must pass all tests before merging.

---

## 📦 Microservices Best Practices

-   Each service should be **self-contained** with its own `Dockerfile`.
-   Use environment variables for config (never hardcode secrets).
-   Log to `stdout` for containerized environments.
-   Keep interfaces between services versioned and documented.

---

## ✅ Checklist Before Merging

-   [ ] Branch is rebased on `dev`.
-   [ ] Code follows naming and formatting conventions.
-   [ ] All tests pass locally.
-   [ ] Service builds and runs inside `docker-compose`.
-   [ ] PR description explains the _why_ and _what_ of changes.
