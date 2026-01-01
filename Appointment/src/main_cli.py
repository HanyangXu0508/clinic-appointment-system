from backup import auto_backup

def main():
    from termin import add_termin, get_termins  # 延迟导入（关键）

    while True:
        print("1 新建  2 查看  0 退出")
        c = input("> ")

        if c == "1":
            print(add_termin(
                input("姓名: "),
                input("日期 DD-MM-YYYY: "),
                input("时间 HH:MM: ")
            ))
        elif c == "2":
            for r in get_termins():
                print(r)
        elif c == "0":
            break

if __name__ == "__main__":
    auto_backup()   # ⭐ 第一件事：备份
    main()