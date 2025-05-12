from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import bot, db, dp
from states.userStates import AdminBroadcast

@dp.message_handler(text='All users')
async def cmd_all_users(message: types.Message):
    # Check if the user is an admin
    is_admin = await check_admin(message.from_user.id)

    if is_admin:
        # Get all users from the database
        all_users = db.get_all_users()

        # Calculate the count of users
        users_count = len(all_users)

        # Send the user count to the admin
        await message.answer(f"Userlar soni: {users_count}")
    else:
        await message.answer("Siz admin emasiz.")

async def check_admin(user_id: int) -> bool:
    # Implement the logic to check if the user is an admin (e.g., check against a list of admin IDs)
    admins = [624301767]  # Replace with actual admin IDs
    return user_id in admins

@dp.message_handler(text='Broadcast')
async def cmd_broadcast(message: types.Message):
    # Check if the user is an admin
    is_admin = await check_admin(message.from_user.id)

    if is_admin:
        # Prompt the admin to enter the broadcast message
        await message.answer("Barcha foydalanuvchilarga uzatmoqchi bo'lgan xabarni kiriting:")
        await AdminBroadcast.BROADCAST.set()
    else:
        await message.answer("Siz admin huquqlariga ega emasiz")


@dp.message_handler(state=AdminBroadcast.BROADCAST)
async def process_broadcast(message: types.Message, state: FSMContext):
    # Get the broadcast message from the admin
    broadcast_message = message.text

    # Get all users from the database
    all_users = db.get_all_users()

    # Send the broadcast message to all users
    for user in all_users:

        try:
            # Send the message to each user
            await bot.send_message(user[3], broadcast_message)
        except Exception as e:
            # Handle errors (e.g., log the error)
            print(f"Error sending broadcast message to user {user[3]}: {e}")

    # Notify the admin that the broadcast is complete
    await message.answer("Habaringiz barcha userlarga bordi!")

    # Reset the state
    await state.finish()


admins = [5449550709,624301767]

download_path = "downloads"




