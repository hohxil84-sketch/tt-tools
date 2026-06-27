import Users from './Users';

/** 系统用户页面 — 仅显示 role=admin 的管理员账号 */
export default function SystemUsers() {
  return <Users roleFilter="admin" />;
}
