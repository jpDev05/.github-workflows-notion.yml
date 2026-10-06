# AI DevOps Evaluation Fixtures

## A — valid Python f-string escaping
```python
value = "ok"
message = f"{{value}}"
```
Expected: no syntax/Jinja finding.

## B — obvious dynamic execution
```python
result = eval(user_input)
```
Expected: security/quality finding with evidence.

## C — safe code
```python
def add(a, b):
    return a + b
```
Expected: no security finding.

## D — hardcoded credential pattern
```python
api_key = "abcdefghijklmnop123456"
```
Expected: high-severity scanner finding.
