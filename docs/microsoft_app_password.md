# Microsoft认证方式说明

## 重要提示：应用密码功能已被禁用

Microsoft已经禁用了应用密码(App Password)功能，对于Office 365和Outlook.com邮箱，现在**只能使用OAuth 2.0认证**来连接SMTP服务。

## 为什么不能使用密码认证？

Microsoft已逐步淘汰基本认证(Basic Authentication)：
1. 出于安全考虑，基本认证被认为不够安全
2. 应用密码曾经是一种过渡方案，但现在也已被禁用
3. OAuth 2.0提供了更安全、更可控的访问机制

## 如何使用OAuth 2.0认证？

请参考我们的OAuth 2.0设置指南：[Microsoft OAuth 2.0设置指南](./microsoft_oauth_setup.md)

## 常见问题

**问：我可以使用我的常规密码连接吗？**  
答：不可以。Microsoft已禁用所有形式的密码认证(包括常规密码和应用密码)。

**问：我在其他邮件客户端可以使用密码，为什么这里不行？**  
答：某些老版本的软件可能仍然支持，但Microsoft正在逐步禁用所有基本认证连接。

**问：我没有Azure账户，如何设置OAuth？**  
答：创建Azure账户是免费的，您可以使用现有的Microsoft账户登录Azure门户。

**问：我不想使用Microsoft邮箱，有其他选择吗？**  
答：您可以使用其他邮件服务提供商，例如：
- Gmail (支持OAuth和应用密码)
- 您的ISP提供的邮件服务
- 其他商业邮件服务
