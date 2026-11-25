# Web Security — Core Concepts
SQL injection happens when untrusted input changes the structure of a database query. Parameterized queries separate input from SQL instructions. A useful investigation starts by identifying where user input reaches data access logic.
Cross-site scripting (XSS) occurs when untrusted content is interpreted as executable browser code. Context-aware output encoding, trusted templating, and appropriate content security policy reduce exposure. Distinguish reflected, stored, and DOM-based XSS while reviewing data flows.
Authentication verifies identity, while authorization determines permissions. Review object ownership checks and role boundaries when diagnosing broken access control.
