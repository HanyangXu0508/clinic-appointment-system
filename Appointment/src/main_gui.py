from backup import auto_backup

def main():
    from ui import TerminApp
    app = TerminApp()
    app.mainloop()

if __name__ == "__main__":
    auto_backup()   # ⭐ 先备份
    main()