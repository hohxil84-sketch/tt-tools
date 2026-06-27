import Users from './Users';

/** 客户端用户页面 — 仅显示 role=user 的普通用户账号 */
export default function ClientUsers() {
  return <Users roleFilter="user" />;
}
