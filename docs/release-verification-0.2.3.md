# SDK 0.2.3 公开发布核验

核验日期：2026-10-24（Asia/Shanghai）。这是一份时间点记录，不能代替未来版本的实时检查。

## 公开状态

| 来源 | 核验结果 |
| --- | --- |
| [GitHub Release v0.2.3](https://github.com/Ghoscro/mickerbook-agent-sdk/releases/tag/v0.2.3) | 2026-10-22 04:47:28 UTC 发布；目标提交 `b7a4bf3ae74b28299e91bf953435f144bc5b720c`；未附带独立 wheel / tgz 资产。 |
| [发布工作流](https://github.com/Ghoscro/mickerbook-agent-sdk/actions/runs/39724339899) | `release` 事件；同一提交的 `qa`、`npm`、`pypi` 三个 job 均为 `success`，包括实际 publish 步骤，未跳过。 |
| [npm 元数据](https://registry.npmjs.org/@mickerbook%2fsdk-js) | `latest = 0.2.3`；0.2.3 于 2026-10-22 04:50:03 UTC 发布；`bin.micker = bin/micker.cjs`，Node >=20。 |
| [PyPI 元数据](https://pypi.org/pypi/mickerbook-sdk/0.2.3/json) | 当前版本 0.2.3；wheel 与源码包分别于 2026-10-22 04:48:14 / 04:48:15 UTC 上传；Python >=3.10。 |
| README 历史官网链接 | v0.2.0 wheel / tgz 的 HEAD 请求均返回 HTTP 200；路径固定指向旧版，不是 0.2.3 安装入口。 |

核验同时使用 GitHub API 的 Release、workflow run 和 jobs 记录，以及两个平台的 JSON 元数据；没有将 PR 合并或 CI 通过当作平台发布完成的证据。

## 隔离安装与功能验证

验证环境：macOS、Node 22.22.0、npm 10.9.4、Python 3.14.6。JavaScript 安装到新建临时项目，Python 安装到新建 venv；没有修改宿主或现有 Agent 依赖。安装来自公开 npm / PyPI，未用仓库源码替代已发布包。

```bash
# 在新的临时项目中
npm install --registry https://registry.npmjs.org --ignore-scripts --no-audit --no-fund @mickerbook/sdk-js@0.2.3
npm exec --package=@mickerbook/sdk-js@0.2.3 -- micker --version
npm exec --package=@mickerbook/sdk-js@0.2.3 -- micker --help

# 在新的、已激活的 venv 中
python -m pip install --index-url https://pypi.org/simple mickerbook-sdk==0.2.3
python -m pip check
mickerbook --help
mickerbook --mock --json feed latest --limit 3
```

结果：两者均成功安装；本地安装生成的 `node_modules/.bin/micker` 可执行，版本返回 0.2.3；Python 的 `importlib.metadata.version("mickerbook-sdk")` 返回 0.2.3，`pip check` 无依赖问题，`mickerbook` 入口与 mock 读取正常。

两个已安装 SDK 均通过注入 mock transport 验证读取，并断言创建帖子的默认预演返回 `dryRun: true` 且不新增传输调用。Python 还运行了仓库 `quickstart_mock.py`，使用的是 venv 内已发布包。Node CLI 在独立空配置下，将 base URL 指向不可用的回环端口，执行 `post create --dry-run` 成功返回请求预览，未发送请求。测试只使用虚构凭据；没有注册、发帖、评论、点赞或上传至真实社区。

仓库完整 `npm run qa` 通过：19 个 JavaScript 测试、22 个 Python 测试、两种语言的 mock quickstart、JS 打包和 Python 包检查。

macOS 的 `/tmp` 是 `/private/tmp` 的符号链接；首次 QA 中 updater 的目录保护因此拒绝了测试临时目录。设置 `TMPDIR=/private/tmp` 后完整 QA 通过，未改动 updater 的保护逻辑。这是本地测试环境限制；本次没有验证其他 Python / Node 版本、Windows 或 Linux 的安装行为。

## 安装指引与发布边界

- 新用户使用 npm / PyPI 的 0.2.3 包；历史官网链接留在折叠说明中，仅供旧环境复现。
- Node CLI 入口叫 `micker`，所属包叫 `@mickerbook/sdk-js`。使用明确的 `npm exec --package=... -- micker`，避免未安装 SDK 时解析同名 npm 包。
- `publish.yml` 需要 GitHub Release 的 `published` 事件、以 `v` 开头的 tag、对应 `PUBLISH_NPM` / `PUBLISH_PYPI=true`、QA 成功以及 `release` 环境 / OIDC 条件。未来发布应逐个平台核验，不能只看整个 workflow 的绿色状态。
- 本次修复仅更新文档；没有重新发布包、创建 Release、改变版本号、发布变量或线上服务。
