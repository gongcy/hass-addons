# gongcy's Home Assistant Add-ons

[English](#english) | [中文](#中文)

---

## English

Home Assistant add-on repository.

### Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**.
2. Open the three-dot menu in the top right and choose **Repositories**.
3. Add:

   ```
   https://github.com/gongcy/hass-addons
   ```

4. The add-ons below appear in the store.

### Add-ons

#### HA Config Git Backup

Periodically backs up your Home Assistant configuration to a Git repository
of your choice. Supports SSH deploy keys and HTTPS tokens, keeps history in
Git, and raises a Home Assistant notification when a backup run fails.

See [its documentation](ha_config_git_backup/DOCS.md) for setup.

**The target repository must be private** — the backup includes `.storage`,
which holds tokens granting full control over your Home Assistant instance.

### Development

```bash
python -m pytest
```

No third-party runtime dependencies; pytest is only needed for development.

### License

MIT

---

## 中文

Home Assistant 加载项仓库。

### 安装

1. 在 Home Assistant 中打开 **设置 → 加载项 → 加载项商店**。
2. 点右上角三点菜单，选 **仓库**。
3. 添加：

   ```
   https://github.com/gongcy/hass-addons
   ```

4. 下列加载项会出现在商店中。

### 加载项

#### HA Config Git Backup

定期把 Home Assistant 配置备份到你指定的 Git 仓库。支持 SSH 部署密钥与
HTTPS 令牌两种认证，用 Git 保存历史，备份失败时在 Home Assistant 中弹出
通知。

配置方法见[它的文档](ha_config_git_backup/DOCS.md)。

**目标仓库必须是私有的**——备份包含 `.storage`，其中有可以完全控制你的
Home Assistant 实例的长期访问令牌。

### 开发

```bash
python -m pytest
```

无第三方运行时依赖，pytest 仅开发期需要。

### 协议

MIT
