from typing import Dict, Any
import ast
import operator

class CalculationAgent:
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    def calculate(self, expression: str, variables: Dict[str, float]) -> Dict[str, Any]:
        try:
            tree = ast.parse(expression, mode='eval')
            result = self._eval_node(tree.body, variables)

            return {
                "result": result,
                "expression": expression,
                "success": True
            }
        except Exception as e:
            return {
                "result": None,
                "error": str(e),
                "success": False
            }

    def _eval_node(self, node, variables):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8 compatibility
            return node.n
        elif isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            raise ValueError(f"Variable {node.id} not found")
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, variables)
            right = self._eval_node(node.right, variables)
            op_type = type(node.op)
            if op_type in self.ALLOWED_OPERATORS:
                return self.ALLOWED_OPERATORS[op_type](left, right)
        raise ValueError("Unsupported operation")
