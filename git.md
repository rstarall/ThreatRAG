
# 新建分支并推送

## 1. 创建新分支并切换到该分支
git checkout -b <new-branch-name>

## 2. 在新分支上进行修改
## ... 编辑文件 ...

## 3. 添加并提交更改
git add .
git commit -m "描述你的更改"

## 4. 推送新分支到远程仓库
git push -u origin <new-branch-name>


#  合并分支
## 1. 拉取远程分支
git fetch origin <branch-name>

## 2. 切换到该分支
git checkout <branch-name>

## 3. 查看分支状态和提交历史
git status
git log --oneline --graph --decorate

## 4. 切换回主分支准备合并
git checkout master

## 5. 查看两个分支的差异
git log master..<branch-name> --oneline
git diff master..<branch-name>

## 6. 如果决定合并，执行合并操作
git merge <branch-name>

## 7. 合并后可以删除已合并的分支（可选）
git branch -d <branch-name>