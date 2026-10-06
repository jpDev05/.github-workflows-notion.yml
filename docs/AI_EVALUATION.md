# AI DevOps Evaluation Standard

The AI review must be measured, not trusted by default.

## Required evaluation classes

### Correct positive
A real defect exists and the reviewer should report it.

### Correct negative
No defect exists and the reviewer should produce no finding.

### False-positive resistance
Valid syntax that looks suspicious must remain valid. For example, Python f-string escaping with double braces must not be reported as a syntax or Jinja error.

### Security precision
Security findings must contain an affected file, added line, concrete evidence, remediation and confidence.

### Line anchoring
A finding without a valid added-line anchor must never become an inline GitHub comment.

## Quality principles

Prefer fewer high-confidence findings, explicit uncertainty, deterministic validation, reproducible fixtures and human verification for critical security findings.

Avoid speculative vulnerabilities, style nitpicks presented as defects, invented test results and invented runtime behavior.
