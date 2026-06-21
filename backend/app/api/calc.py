from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class SumResponse(BaseModel):
    """加算結果のレスポンス。"""

    result: int


@router.get("/calc/sum", response_model=SumResponse)
def sum_numbers(a: int, b: int) -> SumResponse:
    """2 つの整数を加算して返す。

    Args:
        a: 加算する整数 1。
        b: 加算する整数 2。

    Returns:
        a + b を格納した SumResponse。
    """
    return SumResponse(result=a + b)
