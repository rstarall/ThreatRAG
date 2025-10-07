from fastapi import APIRouter
from rag.api.routers.chat_api import chat
from rag.api.routers.data_api import data
from rag.api.routers.graph_api import graph
from rag.api.routers.token_api import auth
#from rag.api.routers.file_api import file

router = APIRouter()
router.include_router(chat)
router.include_router(data)
router.include_router(graph)
router.include_router(auth)
#router.include_router(file)
