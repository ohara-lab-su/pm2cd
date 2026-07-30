from ese774_frame.api_server import FastApiServer
from pm2cd.pm2cd_ctrl import PM2CD
from pm2cd.server_fastapi.routers.pm2cd_router_ctrl import PM2CDRouterCtrl
from pm2cd.server_fastapi.spec_ctrl import pm2cd_ctrl_api_spec

server = FastApiServer(device_cls=PM2CD, router_cls=PM2CDRouterCtrl, api_spec=pm2cd_ctrl_api_spec, device_kwargs={"ip_address": "192.168.1.55", "port": 7777})
app = server.app
