import csv
import json
import logging
import os


def save_to_file(data: dict, path: str):
    """Save receipt data to JSON, JSONL, or CSV."""
    ext = os.path.splitext(path)[1].lower()

    if ext == ".json":
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    elif ext == ".jsonl":
        with open(path, "a") as f:
            f.write(json.dumps(data) + "\n")
    elif ext == ".csv":
        file_exists = os.path.isfile(path)
        with open(path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["store", "item_name", "price", "total"])
            if not file_exists:
                writer.writeheader()

            # If no items, write at least the total
            if not data["items"]:
                 writer.writerow({"store": data["store"], "item_name": "N/A", "price": 0.0, "total": data["total"]})
            else:
                for item in data["items"]:
                    writer.writerow({
                        "store": data["store"],
                        "item_name": item.get("name"),
                        "price": item.get("price"),
                        "total": data["total"]
                    })
    logging.info(f"Result saved to {path}")


def dict_to_table(data):
    print(f"Store: {data['store']}")
    print("-" * 46)

    print(f"{'Item Name':<35} | {'Price':>8}")
    print("-" * 46)

    for item in data["items"]:
        name = item.get("name", "")
        price = item.get("price", None)

        if price is None:
            print(f"{name:<35} | {'':>8}")
        else:
            print(f"{name:<35} | {price:>8.2f}")

    print("-" * 46)

    total = data.get("total")
    if total is None:
        print(f"{'Total':<35} | {'':>8}")
    else:
        print(f"{'Total':<35} | {total:>8.2f}")

