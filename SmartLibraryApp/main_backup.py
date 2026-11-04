
import customtkinter as ctk
from tkinter import messagebox
from database import get_connection
from datetime import datetime, timedelta
import bcrypt

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class SmartLibraryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Smart Library System")
        self.geometry("1000x650")
        self.minsize(850, 580)
        self.configure(fg_color="#F3F6FB")

        self.show_login()

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def make_card(self):
        card = ctk.CTkFrame(
            self,
            width=420,
            corner_radius=18,
            fg_color="white"
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        return card

    def show_login(self):
        self.clear_window()
        card = self.make_card()

        ctk.CTkLabel(
            card,
            text="SMART LIBRARY",
            font=("Segoe UI", 28, "bold"),
            text_color="#17365D"
        ).pack(padx=40, pady=(35, 5))

        ctk.CTkLabel(
            card,
            text="Librarian Login",
            font=("Segoe UI", 16),
            text_color="#667085"
        ).pack(pady=(0, 25))

        self.username_entry = ctk.CTkEntry(
            card,
            width=320,
            height=42,
            placeholder_text="Username"
        )
        self.username_entry.pack(padx=40, pady=8)

        self.password_entry = ctk.CTkEntry(
            card,
            width=320,
            height=42,
            placeholder_text="Password",
            show="*"
        )
        self.password_entry.pack(padx=40, pady=8)

        ctk.CTkButton(
            card,
            text="Log In",
            width=320,
            height=42,
            command=self.login
        ).pack(padx=40, pady=(18, 10))

        ctk.CTkButton(
            card,
            text="Create Librarian Account",
            width=320,
            height=38,
            fg_color="transparent",
            text_color="#2563A6",
            hover_color="#E8EFF8",
            command=self.show_register
        ).pack(padx=40, pady=(0, 30))

    def show_register(self):
        self.clear_window()
        card = self.make_card()

        ctk.CTkLabel(
            card,
            text="Create Account",
            font=("Segoe UI", 26, "bold"),
            text_color="#17365D"
        ).pack(padx=35, pady=(25, 18))

        self.reg_name = ctk.CTkEntry(
            card, width=320, height=38,
            placeholder_text="Full Name"
        )
        self.reg_name.pack(pady=6)

        self.reg_id = ctk.CTkEntry(
            card, width=320, height=38,
            placeholder_text="Librarian ID"
        )
        self.reg_id.pack(pady=6)

        self.reg_username = ctk.CTkEntry(
            card, width=320, height=38,
            placeholder_text="Username"
        )
        self.reg_username.pack(pady=6)

        self.reg_email = ctk.CTkEntry(
            card, width=320, height=38,
            placeholder_text="Email"
        )
        self.reg_email.pack(pady=6)

        self.reg_password = ctk.CTkEntry(
            card, width=320, height=38,
            placeholder_text="Password",
            show="*"
        )
        self.reg_password.pack(pady=6)

        self.reg_confirm = ctk.CTkEntry(
            card, width=320, height=38,
            placeholder_text="Confirm Password",
            show="*"
        )
        self.reg_confirm.pack(pady=6)

        ctk.CTkButton(
            card,
            text="Create Account",
            width=320,
            command=self.register
        ).pack(pady=(14, 6))

        ctk.CTkButton(
            card,
            text="Back to Login",
            width=320,
            fg_color="transparent",
            text_color="#2563A6",
            hover_color="#E8EFF8",
            command=self.show_login
        ).pack(pady=(0, 20))

    def register(self):
        name = self.reg_name.get().strip()
        librarian_id = self.reg_id.get().strip()
        username = self.reg_username.get().strip()
        email = self.reg_email.get().strip()
        password = self.reg_password.get()
        confirm = self.reg_confirm.get()

        if not all([name, librarian_id, username, email, password, confirm]):
            messagebox.showwarning(
                "Missing Information",
                "Please complete all fields."
            )
            return

        if password != confirm:
            messagebox.showerror(
                "Password Error",
                "The passwords do not match."
            )
            return

        if len(password) < 8:
            messagebox.showwarning(
                "Weak Password",
                "Use a password with at least 8 characters."
            )
            return

        connection = None
        cursor = None

        try:
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO librarians
                    (librarian_id, name, username, email, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (librarian_id, name, username, email, password_hash)
            )

            connection.commit()

            messagebox.showinfo(
                "Success",
                "Librarian account created successfully!"
            )
            self.show_login()

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Registration Failed",
                "Could not create the account.\n"
                "The librarian ID, username, or email may already exist.\n\n"
                f"Details: {error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning(
                "Missing Information",
                "Enter your username and password."
            )
            return

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id, librarian_id, name, username, password_hash
                FROM librarians
                WHERE username = %s
                """,
                (username,)
            )
            librarian = cursor.fetchone()

            if librarian and bcrypt.checkpw(
                password.encode("utf-8"),
                librarian["password_hash"].encode("utf-8")
            ):
                messagebox.showinfo(
                    "Login Successful",
                    f"Welcome, {librarian['name']}!"
                )
                self.show_dashboard(librarian)
            else:
                messagebox.showerror(
                    "Login Failed",
                    "Incorrect username or password."
                )

        except Exception as error:
            messagebox.showerror(
                "Database Error",
                f"Could not log in:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def show_dashboard(self, librarian):
        self.clear_window()

        sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0,
            fg_color="#17365D"
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="SMART\nLIBRARY",
            font=("Segoe UI", 25, "bold"),
            text_color="white"
        ).pack(pady=(35, 25))

        ctk.CTkLabel(
            sidebar,
            text=f"Welcome,\n{librarian['name']}",
            font=("Segoe UI", 14),
            text_color="white",
            wraplength=190
        ).pack(pady=(0, 25), padx=10)

        for page in [
            "Dashboard",
            "Borrow Book",
            "Return Book",
            "Book Catalog",
            "Register Student",
            "Add Book",
            "Borrowing History"
        ]:
            ctk.CTkButton(
                sidebar,
                text=page,
                anchor="w",
                fg_color="transparent",
                hover_color="#294F7D",
                text_color="white",
                command=lambda p=page: self.show_page(p, librarian)
            ).pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(
            sidebar,
            text="Log Out",
            fg_color="#A83232",
            hover_color="#852727",
            command=self.show_login
        ).pack(side="bottom", fill="x", padx=12, pady=20)

        self.content = ctk.CTkFrame(
            self, fg_color="#F3F6FB", corner_radius=0
        )
        self.content.pack(
            side="right", fill="both", expand=True,
            padx=25, pady=25
        )

        self.show_page("Dashboard", librarian)

    
    def show_page(self, page, librarian):
        for widget in self.content.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.content,
            text=page,
            font=("Segoe UI", 28, "bold"),
            text_color="#17365D"
        ).pack(anchor="w", pady=(10, 20))

        if page == "Add Book":
            self.show_add_book()
            return

        if page == "Register Student":
            self.show_student_accounts()
            return

        if page == "Book Catalog":
            self.show_book_catalog()
            return

        if page == "Borrow Book":
            self.show_borrow_book(librarian)
            return

        if page == "Return Book":
            self.show_return_book()
            return

        if page == "Borrowing History":
            self.show_borrowing_history()
            return

        if page != "Dashboard":
            ctk.CTkLabel(
                self.content,
                text=f"{page} screen will be implemented next.",
                font=("Segoe UI", 15),
                text_color="#667085"
            ).pack(anchor="w")
            return

        # Retrieve dashboard statistics from MySQL
        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM books")
            total_books = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM loans WHERE return_date IS NULL"
            )
            borrowed = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM loans
                WHERE return_date IS NULL AND due_date < NOW()
                """
            )
            overdue = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    s.full_name,
                    b.title,
                    l.borrow_date,
                    l.due_date,
                    l.return_date
                FROM loans l
                JOIN students s ON s.id = l.student_id
                JOIN books b ON b.id = l.book_id
                ORDER BY l.borrow_date DESC
                LIMIT 8
                """
            )
            activities = cursor.fetchall()

        except Exception as error:
            messagebox.showerror(
                "Dashboard Error",
                f"Could not load dashboard data:\n{error}"
            )
            return

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

        toolbar = ctk.CTkFrame(
            self.content,
            fg_color="#17365D",
            corner_radius=10
        )
        toolbar.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            toolbar,
            text=f"Welcome, {librarian['name']}",
            font=("Segoe UI", 14, "bold"),
            text_color="white"
        ).pack(side="left", padx=16, pady=12)

        catalog_search = ctk.CTkEntry(
            toolbar,
            width=300,
            placeholder_text="Search catalog by title or RFID UID"
        )
        catalog_search.pack(side="right", padx=(0, 10), pady=10)

        def open_catalog_search(_event=None):
            if _event is not None and _event.widget is not catalog_search:
                return
            self.pending_catalog_search = catalog_search.get().strip()
            self.show_page("Book Catalog", librarian)

        catalog_search.bind("<Return>", open_catalog_search)
        ctk.CTkButton(
            toolbar,
            text="Search",
            width=85,
            command=open_catalog_search
        ).pack(side="right", padx=(0, 10), pady=10)

        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x")

        statistics = [
            ("Total Books", total_books, "#17365D"),
            ("Borrowed", borrowed, "#2563A6"),
            ("Overdue", overdue, "#A83232")
        ]

        for title, value, accent in statistics:
            card = ctk.CTkFrame(
                cards,
                fg_color="white",
                corner_radius=14,
                border_width=1,
                border_color="#D0D5DD"
            )
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 12),
                pady=5
            )

            ctk.CTkLabel(
                card,
                text=title.upper(),
                font=("Segoe UI", 12, "bold"),
                text_color="#667085"
            ).pack(anchor="center", padx=18, pady=(16, 4))

            ctk.CTkLabel(
                card,
                text=str(value),
                font=("Segoe UI", 30, "bold"),
                text_color=accent
            ).pack(anchor="center", padx=18, pady=(0, 16))

        action_bar = ctk.CTkFrame(self.content, fg_color="transparent")
        action_bar.pack(fill="x", pady=(15, 8))

        for label, page in (
            ("Borrow Book", "Borrow Book"),
            ("Return Book", "Return Book")
        ):
            ctk.CTkButton(
                action_bar,
                text=label,
                width=140,
                command=lambda target=page: self.show_page(target, librarian)
            ).pack(side="left", padx=(0, 10))

        for label, page in (
            ("Add Book", "Add Book"),
            ("Register Student", "Register Student")
        ):
            ctk.CTkButton(
                action_bar,
                text=label,
                width=145,
                fg_color="#667085",
                hover_color="#475467",
                command=lambda target=page: self.show_page(target, librarian)
            ).pack(side="right", padx=(10, 0))

        activity_heading = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        activity_heading.pack(fill="x", pady=(12, 6))

        ctk.CTkLabel(
            activity_heading,
            text="Recent Activity",
            font=("Segoe UI", 20, "bold"),
            text_color="#17365D"
        ).pack(side="left")

        ctk.CTkButton(
            activity_heading,
            text="View History",
            width=110,
            fg_color="#667085",
            hover_color="#475467",
            command=lambda: self.show_page("Borrowing History", librarian)
        ).pack(side="right")

        activity_frame = ctk.CTkScrollableFrame(
            self.content,
            fg_color="white",
            corner_radius=12
        )
        activity_frame.pack(fill="both", expand=True)
        activity_frame.grid_columnconfigure(0, weight=1)
        activity_frame.grid_columnconfigure(1, weight=1)
        activity_frame.grid_columnconfigure(2, weight=1)
        activity_frame.grid_columnconfigure(3, weight=1)
        activity_frame.grid_columnconfigure(4, weight=1)

        headers = ["Student", "Book", "Borrow Date", "Due Date", "Status"]

        for column, heading in enumerate(headers):
            ctk.CTkLabel(
                activity_frame,
                text=heading,
                font=("Segoe UI", 12, "bold"),
                text_color="#17365D",
                anchor="w"
            ).grid(
                row=0, column=column,
                padx=12, pady=10, sticky="w"
            )

        for row_number, activity in enumerate(activities, start=1):
            student, book, borrow_date, due_date, return_date = activity

            if return_date is not None:
                status = "Returned"
            elif due_date < datetime.now():
                status = "Overdue"
            else:
                status = "Borrowed"

            values = [
                student,
                book,
                str(borrow_date),
                str(due_date),
                status
            ]

            for column, value in enumerate(values):
                ctk.CTkLabel(
                    activity_frame,
                    text=str(value),
                    font=("Segoe UI", 11),
                    text_color="#344054",
                    anchor="w",
                    wraplength=180
                ).grid(
                    row=row_number,
                    column=column,
                    padx=12,
                    pady=10,
                    sticky="ew"
                )

        if not activities:
            ctk.CTkLabel(
                activity_frame,
                text="No borrowing activity yet.",
                text_color="#667085"
            ).grid(row=1, column=0, padx=12, pady=15, sticky="w")

            
    def create_rfid_indicator(
        self,
        parent,
        entry,
        instruction,
        title="RFID SCAN",
        detected_text="RFID UID detected",
        waiting_text="Waiting for RFID scan",
        is_detected=None
    ):
        indicator = ctk.CTkFrame(
            parent,
            width=220,
            fg_color="white",
            corner_radius=14,
            border_width=2,
            border_color="#D0D5DD"
        )
        indicator.pack_propagate(False)

        ctk.CTkLabel(
            indicator,
            text=title,
            font=("Segoe UI", 14, "bold"),
            text_color="#17365D"
        ).pack(pady=(30, 10))

        status = ctk.CTkLabel(
            indicator,
            text=waiting_text,
            font=("Segoe UI", 15, "bold"),
            text_color="#667085",
            wraplength=180
        )
        status.pack(expand=True, padx=15)

        ctk.CTkLabel(
            indicator,
            text=instruction,
            font=("Segoe UI", 12),
            text_color="#667085",
            wraplength=180
        ).pack(padx=15, pady=(0, 25))

        def update_status(_=None):
            detected = (
                is_detected()
                if is_detected is not None
                else bool(entry.get().strip())
            )
            if detected:
                status.configure(
                    text=detected_text,
                    text_color="#16803C"
                )
            else:
                status.configure(
                    text=waiting_text,
                    text_color="#667085"
                )

        entry.bind("<KeyRelease>", update_status)
        return update_status, indicator

    def show_add_book(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.content,
            text="Add Book",
            font=("Segoe UI", 28, "bold"),
            text_color="#17365D"
        ).pack(anchor="w", pady=(10, 20))

        layout = ctk.CTkFrame(self.content, fg_color="transparent")
        layout.pack(fill="x", padx=5, pady=5)

        form = ctk.CTkFrame(
            layout,
            fg_color="white",
            corner_radius=15
        )
        form.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(
            form,
            text="Book Information",
            font=("Segoe UI", 20, "bold"),
            text_color="#17365D"
        ).pack(anchor="w", padx=25, pady=(20, 15))

        self.book_title_entry = ctk.CTkEntry(
            form,
            width=400,
            height=40,
            placeholder_text="Book Title"
        )
        self.book_title_entry.pack(anchor="w", padx=25, pady=8)

        self.book_genre_entry = ctk.CTkEntry(
            form,
            width=400,
            height=40,
            placeholder_text="Genre (e.g. Programming)"
        )
        self.book_genre_entry.pack(anchor="w", padx=25, pady=8)

        self.book_shelf_entry = ctk.CTkEntry(
            form,
            width=400,
            height=40,
            placeholder_text="Shelf Location (e.g. A-01)"
        )
        self.book_shelf_entry.pack(anchor="w", padx=25, pady=8)

        self.book_rfid_entry = ctk.CTkEntry(
            form,
            width=400,
            height=40,
            placeholder_text="RFID UID"
        )
        self.book_rfid_entry.pack(anchor="w", padx=25, pady=8)

        self.book_rfid_indicator_update, indicator = (
            self.create_rfid_indicator(
                layout,
                self.book_rfid_entry,
                "Scan a book tag into the RFID UID field."
            )
        )
        indicator.pack(side="left", fill="both", padx=(0, 15))

        ctk.CTkButton(
            form,
            text="Save Book",
            width=180,
            height=42,
            command=self.save_book
        ).pack(anchor="w", padx=25, pady=(18, 25))

    def save_book(self):
        title = self.book_title_entry.get().strip()
        genre = self.book_genre_entry.get().strip()
        shelf = self.book_shelf_entry.get().strip()
        rfid_uid = self.book_rfid_entry.get().strip()

        if not title or not rfid_uid:
            messagebox.showwarning(
                "Missing Information",
                "Book title and RFID UID are required."
            )
            return

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO books (title, genre, shelf, rfid_uid)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    title,
                    genre or None,
                    shelf or None,
                    rfid_uid
                )
            )

            connection.commit()

            messagebox.showinfo(
                "Success",
                "Book added successfully!"
            )

            self.book_title_entry.delete(0, "end")
            self.book_genre_entry.delete(0, "end")
            self.book_shelf_entry.delete(0, "end")
            self.book_rfid_entry.delete(0, "end")
            self.book_rfid_indicator_update()

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Unable to Add Book",
                "Could not save the book.\n"
                "Check whether the RFID UID is already registered.\n\n"
                f"Details: {error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    def show_student_accounts(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.content,
            text="Register Student",
            font=("Segoe UI", 28, "bold"),
            text_color="#17365D"
        ).pack(anchor="w", pady=(10, 20))

        layout = ctk.CTkFrame(self.content, fg_color="transparent")
        layout.pack(fill="x", padx=5, pady=5)

        form = ctk.CTkFrame(
            layout,
            fg_color="white",
            corner_radius=15
        )
        form.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(
            form,
            text="Register Student",
            font=("Segoe UI", 20, "bold"),
            text_color="#17365D"
        ).pack(anchor="w", padx=25, pady=(20, 15))

        self.student_no_entry = ctk.CTkEntry(
            form,
            width=400,
            height=40,
            placeholder_text="Student Number"
        )
        self.student_no_entry.pack(anchor="w", padx=25, pady=8)

        self.student_name_entry = ctk.CTkEntry(
            form,
            width=400,
            height=40,
            placeholder_text="Full Name"
        )
        self.student_name_entry.pack(anchor="w", padx=25, pady=8)

        self.student_email_entry = ctk.CTkEntry(
            form,
            width=400,
            height=40,
            placeholder_text="Email (optional)"
        )
        self.student_email_entry.pack(anchor="w", padx=25, pady=8)

        self.student_rfid_entry = ctk.CTkEntry(
            form,
            width=400,
            height=40,
            placeholder_text="RFID UID"
        )
        self.student_rfid_entry.pack(anchor="w", padx=25, pady=8)

        self.student_rfid_indicator_update, indicator = (
            self.create_rfid_indicator(
                layout,
                self.student_rfid_entry,
                "Scan a student card into the RFID UID field."
            )
        )
        indicator.pack(side="left", fill="both", padx=(0, 15))

        ctk.CTkButton(
            form,
            text="Register Student",
            width=180,
            height=42,
            command=self.save_student
        ).pack(anchor="w", padx=25, pady=(18, 25))

        ctk.CTkLabel(
            self.content,
            text="Registered Students",
            font=("Segoe UI", 20, "bold"),
            text_color="#17365D"
        ).pack(anchor="w", pady=(25, 10))

        self.student_list = ctk.CTkScrollableFrame(
            self.content,
            fg_color="white",
            corner_radius=12
        )
        self.student_list.pack(fill="both", expand=True)

        self.load_students()

    def save_student(self):
        student_no = self.student_no_entry.get().strip()
        full_name = self.student_name_entry.get().strip()
        email = self.student_email_entry.get().strip()
        rfid_uid = self.student_rfid_entry.get().strip()

        if not student_no or not full_name or not rfid_uid:
            messagebox.showwarning(
                "Missing Information",
                "Student number, full name, and RFID UID are required."
            )
            return

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO students
                    (student_no, full_name, email, rfid_uid)
                VALUES (%s, %s, %s, %s)
                """,
                (student_no, full_name, email or None, rfid_uid)
            )
            connection.commit()

            messagebox.showinfo(
                "Success",
                "Student registered successfully!"
            )

            self.student_no_entry.delete(0, "end")
            self.student_name_entry.delete(0, "end")
            self.student_email_entry.delete(0, "end")
            self.student_rfid_entry.delete(0, "end")
            self.student_rfid_indicator_update()

            self.load_students()

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Registration Failed",
                "Could not register student. The student number "
                "or RFID UID may already exist.\n\n"
                f"Details: {error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def load_students(self):
        for widget in self.student_list.winfo_children():
            widget.destroy()

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT student_no, full_name, email, rfid_uid
                FROM students
                ORDER BY full_name
                """
            )
            students = cursor.fetchall()

            headers = [
                "Student Number", "Full Name", "Email", "RFID UID"
            ]

            for column, heading in enumerate(headers):
                ctk.CTkLabel(
                    self.student_list,
                    text=heading,
                    font=("Segoe UI", 12, "bold"),
                    text_color="#17365D",
                    anchor="w"
                ).grid(
                    row=0, column=column,
                    padx=10, pady=10, sticky="w"
                )

            for row_number, student in enumerate(students, start=1):
                for column, value in enumerate(student):
                    ctk.CTkLabel(
                        self.student_list,
                        text=value if value else "-",
                        font=("Segoe UI", 11),
                        text_color="#344054",
                        anchor="w",
                        wraplength=160
                    ).grid(
                        row=row_number,
                        column=column,
                        padx=10, pady=8, sticky="w"
                    )

            if not students:
                ctk.CTkLabel(
                    self.student_list,
                    text="No students registered yet.",
                    text_color="#667085"
                ).grid(row=1, column=0, padx=10, pady=15)

        except Exception as error:
            messagebox.showerror(
                "Database Error",
                f"Could not load students:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    def show_book_catalog(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.content,
            text="Book Catalog",
            font=("Segoe UI", 28, "bold"),
            text_color="#17365D"
        ).pack(anchor="w", pady=(10, 15))

        toolbar = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        toolbar.pack(fill="x", pady=(0, 12))

        self.book_search_entry = ctk.CTkEntry(
            toolbar,
            width=360,
            height=38,
            placeholder_text="Search by title or RFID UID"
        )
        self.book_search_entry.pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        self.book_search_entry.bind(
            "<Return>",
            lambda event: (
                self.load_book_catalog()
                if event.widget is self.book_search_entry else None
            )
        )

        ctk.CTkButton(
            toolbar,
            text="Search",
            width=100,
            command=self.load_book_catalog
        ).pack(side="left", padx=(0, 10))

        self.book_status_filter = ctk.CTkComboBox(
            toolbar,
            values=["All statuses", "Available", "Borrowed"],
            width=145,
            state="readonly",
            command=lambda selected: (
                self.load_book_catalog()
                if selected == self.book_status_filter.get() else None
            )
        )
        self.book_status_filter.set("All statuses")
        self.book_status_filter.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            toolbar,
            text="Show All",
            width=100,
            fg_color="#667085",
            hover_color="#475467",
            command=self.clear_book_search
        ).pack(side="left")

        self.book_catalog_frame = ctk.CTkScrollableFrame(
            self.content,
            fg_color="white",
            corner_radius=12
        )
        self.book_catalog_frame.pack(fill="both", expand=True)
        self.book_catalog_frame.grid_columnconfigure(0, weight=3)
        self.book_catalog_frame.grid_columnconfigure(1, weight=2)
        self.book_catalog_frame.grid_columnconfigure(2, weight=1)
        self.book_catalog_frame.grid_columnconfigure(3, weight=1)

        self.book_search_entry.insert(
            0, getattr(self, "pending_catalog_search", "")
        )
        self.pending_catalog_search = ""

        self.load_book_catalog()

    def clear_book_search(self):
        self.book_search_entry.delete(0, "end")
        self.book_status_filter.set("All statuses")
        self.load_book_catalog()

    def load_book_catalog(self):
        for widget in self.book_catalog_frame.winfo_children():
            widget.destroy()

        search_text = self.book_search_entry.get().strip()
        status_filter = self.book_status_filter.get()

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            query = """
                SELECT
                    b.title,
                    b.rfid_uid,
                    b.shelf,
                    CASE
                        WHEN EXISTS (
                            SELECT 1
                            FROM loans l
                            WHERE l.book_id = b.id
                              AND l.return_date IS NULL
                        )
                        THEN 'Borrowed'
                        ELSE 'Available'
                    END AS book_status
                FROM books b
                WHERE (
                    b.title LIKE %s
                    OR b.rfid_uid LIKE %s
                )
            """

            search_pattern = f"%{search_text}%"
            parameters = [search_pattern, search_pattern]

            if status_filter == "Available":
                query += """
                    AND NOT EXISTS (
                        SELECT 1
                        FROM loans l
                        WHERE l.book_id = b.id
                          AND l.return_date IS NULL
                    )
                """
            elif status_filter == "Borrowed":
                query += """
                    AND EXISTS (
                        SELECT 1
                        FROM loans l
                        WHERE l.book_id = b.id
                          AND l.return_date IS NULL
                    )
                """

            cursor.execute(query + " ORDER BY b.title", tuple(parameters))

            books = cursor.fetchall()

            headers = ["Title", "RFID UID", "Shelf", "Status"]

            for column, heading in enumerate(headers):
                ctk.CTkLabel(
                    self.book_catalog_frame,
                    text=heading,
                    font=("Segoe UI", 12, "bold"),
                    text_color="#17365D",
                    anchor="w"
                ).grid(
                    row=0,
                    column=column,
                    padx=12,
                    pady=10,
                    sticky="ew"
                )

            for row_number, book in enumerate(books, start=1):
                title, rfid_uid, shelf, status = book
                values = [title, rfid_uid, shelf]

                for column, value in enumerate(values):
                    ctk.CTkLabel(
                        self.book_catalog_frame,
                        text=str(value) if value is not None else "-",
                        font=("Segoe UI", 11),
                        text_color="#344054",
                        anchor="w",
                        wraplength=220
                    ).grid(
                        row=row_number,
                        column=column,
                        padx=12,
                        pady=8,
                        sticky="ew"
                    )

                status_color = (
                    "#2563A6" if status == "Available" else "#A83232"
                )
                ctk.CTkLabel(
                    self.book_catalog_frame,
                    text=status,
                    fg_color=status_color,
                    text_color="white",
                    corner_radius=8,
                    font=("Segoe UI", 10, "bold")
                ).grid(
                    row=row_number,
                    column=3,
                    padx=12,
                    pady=6,
                    sticky="e"
                )

            if not books:
                ctk.CTkLabel(
                    self.book_catalog_frame,
                    text="No matching books found.",
                    text_color="#667085"
                ).grid(
                    row=1, column=0, columnspan=4,
                    padx=12, pady=15, sticky="w"
                )

        except Exception as error:
            messagebox.showerror(
                "Book Catalog Error",
                f"Could not load books:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    def show_borrow_book(self, librarian):
        for widget in self.content.winfo_children():
            widget.destroy()

        self.available_book_map = {}

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(20, 5))

        ctk.CTkLabel(
            header,
            text="Borrow Book",
            font=("Arial", 26, "bold")
        ).pack(side="left")

        ctk.CTkLabel(
            self.content,
            text="Register a student's book loan (maximum 7 days).",
            font=("Arial", 13)
        ).pack(anchor="w", padx=30, pady=(0, 20))

        layout = ctk.CTkFrame(self.content, fg_color="transparent")
        layout.pack(fill="x", padx=30, pady=10)

        form = ctk.CTkFrame(layout)
        form.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(
            form,
            text="Student Number or RFID UID"
        ).pack(anchor="w", padx=20, pady=(20, 5))

        student_entry = ctk.CTkEntry(
            form,
            placeholder_text="Enter student number or RFID UID",
            width=350
        )
        student_entry.pack(anchor="w", padx=20, pady=(0, 15))

        self.borrow_rfid_indicator_update, indicator = (
            self.create_rfid_indicator(
                layout,
                student_entry,
                "Scan the student's RFID card or enter their student number.",
                title="RFID / STUDENT ID",
                detected_text="Student identifier received"
            )
        )
        indicator.pack(side="left", fill="both", padx=(0, 15))

        ctk.CTkLabel(
            form,
            text="Select Available Book"
        ).pack(anchor="w", padx=20, pady=(0, 5))

        book_combo = ctk.CTkComboBox(
            form,
            values=["Loading books..."],
            width=350,
            state="readonly"
        )
        book_combo.pack(anchor="w", padx=20, pady=(0, 15))

        ctk.CTkLabel(
            form,
            text="Loan Duration (1–7 days)"
        ).pack(anchor="w", padx=20, pady=(0, 5))

        duration_entry = ctk.CTkEntry(
            form,
            placeholder_text="Enter number of days (1–7)",
            width=350
        )
        duration_entry.pack(anchor="w", padx=20, pady=(0, 20))

        ctk.CTkButton(
            form,
            text="Confirm Borrow",
            command=lambda: self.borrow_book(
                student_entry,
                book_combo,
                duration_entry
            ),
            width=180,
            height=38
        ).pack(anchor="w", padx=20, pady=(0, 20))

        self.load_available_books(book_combo)

    def load_available_books(self, book_combo):
        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT b.id, b.title, b.shelf
                FROM books b
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM loans l
                    WHERE l.book_id = b.id
                    AND l.return_date IS NULL
                )
                ORDER BY b.title
            """)

            books = cursor.fetchall()
            self.available_book_map = {}

            for book_id, title, shelf in books:
                display = f"{book_id} | {title} | Shelf: {shelf or 'N/A'}"
                self.available_book_map[display] = book_id

            if books:
                book_combo.configure(
                    values=list(self.available_book_map.keys())
                )
                book_combo.set(list(self.available_book_map.keys())[0])
            else:
                book_combo.configure(values=["No available books"])
                book_combo.set("No available books")

        except Exception as error:
            messagebox.showerror(
                "Database Error",
                f"Could not load available books:\n{error}"
            )

        finally:
            if "cursor" in locals():
                cursor.close()
            if "connection" in locals() and connection.is_connected():
                connection.close()

    def borrow_book(self, student_entry, book_combo, duration_entry):
        student_identifier = student_entry.get().strip()
        selected_book = book_combo.get().strip()
        duration_text = duration_entry.get().strip()

        if not student_identifier:
            messagebox.showwarning(
                "Missing Student",
                "Enter the student's number or RFID UID."
            )
            return

        if selected_book not in self.available_book_map:
            messagebox.showwarning(
                "No Book Selected",
                "Please select an available book."
            )
            return

        try:
            days = int(duration_text)
        except ValueError:
            messagebox.showwarning(
                "Invalid Duration",
                "Enter a whole number from 1 to 7."
            )
            return

        if not 1 <= days <= 7:
            messagebox.showwarning(
                "Invalid Duration",
                "Loan duration must be between 1 and 7 days."
            )
            return

        book_id = self.available_book_map[selected_book]
        connection = None
        cursor = None

        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT id, full_name
                FROM students
                WHERE student_no = %s OR rfid_uid = %s
                LIMIT 1
            """, (student_identifier, student_identifier))

            student = cursor.fetchone()

            if not student:
                connection.rollback()
                messagebox.showerror(
                    "Student Not Found",
                    "No student matches that student number or RFID UID."
                )
                return

            student_id, student_name = student

            # Check again in case another loan was created after loading.
            cursor.execute("""
                SELECT id
                FROM books
                WHERE id = %s
                FOR UPDATE
            """, (book_id,))

            if not cursor.fetchone():
                connection.rollback()
                messagebox.showerror(
                    "Book Not Found",
                    "This book no longer exists."
                )
                return

            cursor.execute("""
                SELECT id
                FROM loans
                WHERE book_id = %s
                AND return_date IS NULL
                LIMIT 1
            """, (book_id,))

            if cursor.fetchone():
                connection.rollback()
                messagebox.showwarning(
                    "Book Unavailable",
                    "This book has already been borrowed. Refresh the list."
                )
                self.load_available_books(book_combo)
                return

            borrow_date = datetime.now()
            due_date = borrow_date + timedelta(days=days)

            cursor.execute("""
                INSERT INTO loans
                    (student_id, book_id, borrow_date,
                     due_date, return_date, penalty)
                VALUES (%s, %s, %s, %s, NULL, 0)
            """, (student_id, book_id, borrow_date, due_date))

            connection.commit()

            messagebox.showinfo(
                "Borrow Successful",
                f"Student: {student_name}\n"
                f"Borrow duration: {days} day(s)\n"
                f"Borrow date: {borrow_date:%Y-%m-%d}\n"
                f"Due date: {due_date:%Y-%m-%d}"
            )

            student_entry.delete(0, "end")
            duration_entry.delete(0, "end")
            self.borrow_rfid_indicator_update()

            self.load_available_books(book_combo)

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Borrowing Error",
                f"Could not process the loan:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    def show_return_book(self):
        parent = self.content

        for widget in parent.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            parent,
            text="Return Book",
            font=("Arial", 26, "bold"),
            text_color="#17365D"
        ).pack(anchor="w", padx=30, pady=(20, 5))

        ctk.CTkLabel(
            parent,
            text="Select an active loan and confirm the book return.",
            font=("Arial", 13),
            text_color="#667085"
        ).pack(anchor="w", padx=30, pady=(0, 20))

        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.pack(fill="x", padx=30, pady=10)

        selection_panel = ctk.CTkFrame(
            layout,
            fg_color="#D9D9D9",
            corner_radius=12
        )
        selection_panel.pack(side="right", fill="both", expand=True)

        loan_combo = ctk.CTkComboBox(
            selection_panel,
            values=["Loading active loans..."],
            width=450,
            state="readonly",
            command=self.update_return_preview
        )
        loan_combo.pack(anchor="w", padx=15, pady=(15, 10))
        loan_combo.set("")

        self.active_loan_map = {}
        self.active_loan_details = {}
        self.return_rfid_indicator_update, indicator = (
            self.create_rfid_indicator(
                layout,
                loan_combo,
                "Select an active loan to preview its details.",
                detected_text="Loan selected",
                waiting_text="Waiting for loan selection",
                is_detected=lambda: (
                    loan_combo.get() in self.active_loan_details
                )
            )
        )
        indicator.pack(side="left", fill="both", padx=(0, 10))

        self.return_preview_values = {}
        for key, label in (
            ("student", "Student"),
            ("book", "Book"),
            ("due_date", "Due Date")
        ):
            card = ctk.CTkFrame(
                selection_panel,
                fg_color="white",
                corner_radius=10
            )
            card.pack(fill="x", padx=15, pady=5)

            ctk.CTkLabel(
                card,
                text=label,
                font=("Segoe UI", 11, "bold"),
                text_color="#667085"
            ).pack(anchor="w", padx=12, pady=(9, 0))

            self.return_preview_values[key] = ctk.CTkLabel(
                card,
                text="—",
                font=("Segoe UI", 13, "bold"),
                text_color="#17365D",
                wraplength=500,
                justify="left"
            )
            self.return_preview_values[key].pack(
                anchor="w", padx=12, pady=(2, 9)
            )

        self.return_due_status = ctk.CTkLabel(
            selection_panel,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color="#667085",
            wraplength=500
        )
        self.return_due_status.pack(anchor="w", padx=15, pady=(4, 8))

        ctk.CTkButton(
            selection_panel,
            text="Confirm Return",
            width=180,
            height=40,
            command=lambda: self.process_return(loan_combo)
        ).pack(anchor="w", padx=15, pady=(5, 8))

        ctk.CTkButton(
            selection_panel,
            text="Refresh List",
            width=180,
            fg_color="#667085",
            hover_color="#475467",
            command=lambda: self.load_active_loans(loan_combo)
        ).pack(anchor="w", padx=15, pady=(0, 15))

        self.load_active_loans(loan_combo)

    def update_return_preview(self, selected):
        self.return_rfid_indicator_update()
        loan_details = self.active_loan_details.get(selected)

        if not loan_details:
            for value_label in self.return_preview_values.values():
                value_label.configure(text="—")
            self.return_due_status.configure(text="")
            return

        student_name, book_title, due_date = loan_details
        self.return_preview_values["student"].configure(text=student_name)
        self.return_preview_values["book"].configure(text=book_title)
        self.return_preview_values["due_date"].configure(
            text=due_date.strftime("%b %d, %Y")
            if hasattr(due_date, "strftime") else str(due_date)
        )

        due_day = due_date.date() if isinstance(due_date, datetime) else due_date
        today = datetime.now().date()
        if due_day < today:
            days_overdue = (today - due_day).days
            status = f"Overdue by {days_overdue} day(s)"
            color = "#B42318"
        elif due_day == today:
            status = "Due today"
            color = "#B54708"
        else:
            days_remaining = (due_day - today).days
            status = f"{days_remaining} day(s) until due"
            color = "#16803C"

        self.return_due_status.configure(text=status, text_color=color)

    def load_active_loans(self, loan_combo):
        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT l.id, s.full_name, b.title, l.due_date
                FROM loans l
                JOIN students s ON s.id = l.student_id
                JOIN books b ON b.id = l.book_id
                WHERE l.return_date IS NULL
                ORDER BY l.due_date ASC
            """)

            rows = cursor.fetchall()
            self.active_loan_map = {}
            self.active_loan_details = {}

            for loan_id, student_name, book_title, due_date in rows:
                label = f"Loan #{loan_id} | {student_name} | {book_title}"
                self.active_loan_map[label] = loan_id
                self.active_loan_details[label] = (
                    student_name,
                    book_title,
                    due_date
                )

            if rows:
                options = list(self.active_loan_map.keys())
                loan_combo.configure(values=options)
                loan_combo.set(options[0])
                self.update_return_preview(options[0])
            else:
                loan_combo.configure(values=["No active loans"])
                loan_combo.set("No active loans")
                self.update_return_preview("No active loans")

        except Exception as error:
            messagebox.showerror(
                "Database Error",
                f"Could not load active loans:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def process_return(self, loan_combo):
        selected = loan_combo.get()

        if selected not in self.active_loan_map:
            messagebox.showwarning(
                "No Loan Selected",
                "Please select an active borrowing record."
            )
            return

        loan_id = self.active_loan_map[selected]
        connection = None
        cursor = None

        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT l.due_date, s.full_name, b.title
                FROM loans l
                JOIN students s ON s.id = l.student_id
                JOIN books b ON b.id = l.book_id
                WHERE l.id = %s AND l.return_date IS NULL
                FOR UPDATE
            """, (loan_id,))

            loan = cursor.fetchone()

            if not loan:
                connection.rollback()
                messagebox.showwarning(
                    "Already Returned",
                    "This loan has already been returned. Refresh the list."
                )
                self.load_active_loans(loan_combo)
                return

            due_date, student_name, book_title = loan

            # Record the return. Penalty stays unchanged until a penalty
            # policy is defined for the project.
            cursor.execute("""
                UPDATE loans
                SET return_date = NOW()
                WHERE id = %s AND return_date IS NULL
            """, (loan_id,))

            connection.commit()

            messagebox.showinfo(
                "Return Successful",
                f"Student: {student_name}\n"
                f"Book: {book_title}\n"
                f"Due date: {due_date}\n"
                "The book has been marked as returned."
            )

            self.load_active_loans(loan_combo)

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Return Error",
                f"Could not process the return:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    def show_borrowing_history(self):
        parent = self.content

        ctk.CTkLabel(
            parent,
            text="Borrowing History",
            font=("Arial", 26, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))

        ctk.CTkLabel(
            parent,
            text="View all current and previous borrowing transactions."
        ).pack(anchor="w", padx=20, pady=(0, 15))

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=(0, 10))

        search_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="Search student or book title",
            width=300
        )
        search_entry.pack(side="left", padx=(0, 10))

        history_frame = ctk.CTkScrollableFrame(parent)
        history_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        def load_history():
            for widget in history_frame.winfo_children():
                widget.destroy()

            connection = None
            cursor = None

            try:
                connection = get_connection()
                cursor = connection.cursor()

                search_text = search_entry.get().strip()

                cursor.execute("""
                    SELECT
                        l.id,
                        s.full_name,
                        b.title,
                        l.borrow_date,
                        l.due_date,
                        l.return_date,
                        l.penalty
                    FROM loans l
                    JOIN students s ON s.id = l.student_id
                    JOIN books b ON b.id = l.book_id
                    WHERE s.full_name LIKE %s
                       OR b.title LIKE %s
                    ORDER BY l.borrow_date DESC, l.id DESC
                """, (
                    f"%{search_text}%",
                    f"%{search_text}%"
                ))

                rows = cursor.fetchall()

                headers = [
                    "Loan ID",
                    "Student",
                    "Book",
                    "Borrow Date",
                    "Due Date",
                    "Return Date",
                    "Penalty",
                    "Status"
                ]

                header_frame = ctk.CTkFrame(history_frame)
                header_frame.pack(fill="x", pady=(0, 5))

                for column, heading in enumerate(headers):
                    ctk.CTkLabel(
                        header_frame,
                        text=heading,
                        font=("Arial", 11, "bold"),
                        width=105
                    ).grid(
                        row=0,
                        column=column,
                        padx=2,
                        pady=8,
                        sticky="w"
                    )

                if not rows:
                    ctk.CTkLabel(
                        history_frame,
                        text="No borrowing records found."
                    ).pack(anchor="w", padx=10, pady=10)
                    return

                for row in rows:
                    (
                        loan_id,
                        student_name,
                        book_title,
                        borrow_date,
                        due_date,
                        return_date,
                        penalty
                    ) = row

                    if return_date is not None:
                        status = "Returned"
                    elif due_date < datetime.now():
                        status = "Overdue"
                    else:
                        status = "Borrowed"

                    values = [
                        str(loan_id),
                        student_name,
                        book_title,
                        str(borrow_date),
                        str(due_date),
                        str(return_date) if return_date else "Not returned",
                        f"{float(penalty or 0):.2f}",
                        status
                    ]

                    row_frame = ctk.CTkFrame(
                        history_frame,
                        fg_color="transparent"
                    )
                    row_frame.pack(fill="x", pady=2)

                    for column, value in enumerate(values):
                        ctk.CTkLabel(
                            row_frame,
                            text=value,
                            width=105,
                            anchor="w",
                            wraplength=100
                        ).grid(
                            row=0,
                            column=column,
                            padx=2,
                            pady=6,
                            sticky="w"
                        )

            except Exception as error:
                messagebox.showerror(
                    "History Error",
                    f"Could not load borrowing history:\n{error}"
                )

            finally:
                if cursor:
                    cursor.close()
                if connection and connection.is_connected():
                    connection.close()

        ctk.CTkButton(
            toolbar,
            text="Search",
            command=load_history
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            toolbar,
            text="Refresh",
            fg_color="gray",
            command=load_history
        ).pack(side="left")

        load_history()


if __name__ == "__main__":
    app = SmartLibraryApp()
    app.mainloop()
