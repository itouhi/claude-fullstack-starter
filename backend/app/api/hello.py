from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HelloResponse(BaseModel):
    """挨拶メッセージのレスポンス。"""

    message: str


@router.get("/hello", response_model=HelloResponse)
def hello(name: str = "world") -> HelloResponse:
    """名前を受け取り挨拶メッセージを返す。

    Args:
        name: 挨拶する相手の名前。

    Returns:
        `Hello, {name}!` を格納した HelloResponse。
    """
    return HelloResponse(message=f"Hello, {name}!")
