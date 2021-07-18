import os
import cs50

# from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
    
# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
# db = SQL("sqlite:///finance.db")
db = cs50.SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT symbol, SUM(shares) AS Total FROM user_transaction WHERE user_id = :id GROUP BY symbol", id = session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id = :id ", id = session["user_id"])

    portfolio ={}
    grand_total = []

    #input stocks value in a dict. Use of nested dict
    for stock in stocks:
        portfolio[stock["symbol"]] = lookup(stock["symbol"])

    #iterate the dict and add new element in nested dict
    counter = 0
    for k in list(portfolio):
        #If number of shares is 0 remove from dict
        if stocks[counter]['Total'] == 0:
            portfolio.pop(k)
            counter += 1
            continue
        portfolio[k]['shares'] = stocks[counter]['Total']
        portfolio[k]['total'] = portfolio[k]['shares'] * portfolio[k]['price']
        #add total cash value to the grand_total list
        grand_total.append(portfolio[k]['total'])
        counter += 1

    cash_remaining = cash[0]["cash"]

    #calculate total cash by summing remaining cash and sum of total cash list
    cash_total = sum(grand_total) + cash_remaining

    return render_template("index.html",portfolio = portfolio, cash_remaining = cash_remaining, cash_total=cash_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        symbol = request.form.get("symbol")
        print(symbol)
        #Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("Missing symbol")

        #Ensure symbol is valid
        elif lookup(symbol) == None:
            return apology("Invalid symbol")

        elif not request.form.get("shares"):
            return apology("Missing shares")

        #Look up price of symbol and input in price
        stock = lookup(symbol)
        shares = int(request.form.get("shares"))

        rows = db.execute("SELECT cash FROM users WHERE id = :id ", id = session["user_id"])
        cash = rows[0]["cash"]

        price = shares * stock['price']

        updated_cash = cash - price

        if updated_cash < 0:
            return apology("Not enough cash")

        db.execute("UPDATE users SET cash = :updated_cash WHERE id = :id", updated_cash = updated_cash, id = session["user_id"])
        db.execute("INSERT INTO user_transaction(user_ID, symbol, shares, price, time) VALUES(:userID, :symbol, :shares, :price, CURRENT_TIMESTAMP)", userID = session["user_id"], symbol = symbol, shares = shares, price = price)
        flash('Bought !')
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    if request.method == "GET":
        history = db.execute("SELECT * FROM user_transaction WHERE user_id = :id", id = session["user_id"])

        h_portfolio = {}
        for stock in history:
            h_portfolio[stock['id']] = stock

        # for i, k in enumerate(history):
        #     h_portfolio[k]['symbol'] = history[k]['symbol']
        #     h_portfolio[k]

        return render_template("history.html", history = h_portfolio
        )


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        symbol = request.form.get("quote")

        #Ensure quote was submitted
        if not request.form.get("quote"):
            return apology("Missing symbol")

        #Ensure symbol is valid
        elif lookup(symbol) == None:
            return apology("Invalid symbol")

        else:
            result = lookup(symbol)
            return render_template("quoted.html", companyname = result["name"], latestPrice = result["price"], symbol = result["symbol"])

    if request.method == "GET":
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        #Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        #Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        #Ensure confirm password was submitted
        elif not request.form.get("confirm_password"):
            return apology("must confirm password", 403)

        #Check if password match
        elif request.form.get("password") != request.form.get("confirm_password"):
            return apology("password do not match", 403)

        #Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        #check if username already taken
        if len(rows) == 1:
            return apology("Username already taken", 403)


        #generate hash password
        hash_value = generate_password_hash(request.form.get("password"))

        #insert user into database
        db.execute("INSERT INTO users(username, hash) VALUES(:username, :hash)", username = request.form.get("username"), hash=hash_value)
        return render_template("login.html")

    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        if not request.form.get("stock"):
            return apology("Please select a stock", 403)
        elif not request.form.get("shares"):
            return apology("Please input number of shares to sell")

        stock = request.form.get("stock")
        shares = int(request.form.get("shares"))

        stocks = lookup(stock)

        #get user current cash
        row = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"] )
        current_cash = row[0]["cash"]
        #get total shares user hold
        shares_num = db.execute("SELECT SUM(shares) as total FROM user_transaction WHERE user_id = :id AND symbol = :symbol", id = session["user_id"], symbol = stock)

        #Verify if user can sell share
        if shares_num[0]['total'] - shares < 0:
            return apology("You don't have that many shares to sell", 403)
        else:
            gain = stocks["price"] * shares

            updated_cash = current_cash + gain

            db.execute("UPDATE users SET cash = :updated_cash WHERE id = :id", updated_cash = updated_cash, id = session["user_id"])
            db.execute("INSERT INTO user_transaction(user_ID, symbol, shares, price, time) VALUES(:userID, :symbol, :shares, :price, CURRENT_TIMESTAMP)", userID = session["user_id"], symbol = stock, shares = -shares, price = gain)
            flash('Sold!')
            return redirect('/')

    if request.method == "GET":
        stocks = db.execute("SELECT symbol, SUM(shares) as Total FROM user_transaction WHERE user_id = :id GROUP BY symbol", id = session["user_id"])

        symbol = []

        for i in range(len(stocks)):
            if stocks[i]['Total'] == 0:
                continue
            symbol.append(stocks[i]['symbol'])

        return render_template("sell.html", symbol = symbol)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "GET":

        user = db.execute("SELECT username, cash FROM users WHERE id = :id", id = session["user_id"])
        shares = db.execute("SELECT SUM(shares) as total FROM user_transaction WHERE user_id = :id", id = session["user_id"])

        return render_template("profile.html", user = user, shares = shares)

@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    if request.method =="POST":
        if not request.form.get("addcash"):
            return apology("Please insert amount of money", 403)

        addcash = int(request.form.get("addcash"))
        user_cash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])

        updated_cash = user_cash[0]['cash'] + addcash

        db.execute("UPDATE users SET cash = :updated_cash WHERE id = :id", updated_cash = updated_cash, id = session["user_id"])
        flash("Cash added !")
        return redirect("/profile")

    else:
        return render_template("addcash.html")



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
