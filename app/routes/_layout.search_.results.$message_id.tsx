import { type LoaderFunctionArgs } from '@remix-run/node'
import { json, useLoaderData, useParams } from '@remix-run/react'
import { useState } from 'react'
import { requireSession } from '~/lib/auth'
import { api, API_URL } from '~/lib/utils'

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { session } = await requireSession(request)

  const messageId = params.message_id
  const message = await api(`/messages/${messageId}`, {
    headers: {
      cookie: session,
    },
  })

  return json({ message })
}

export default function Message() {
  // @ts-ignore
  const { message } = useLoaderData()
  const params = useParams()
  if (!params.message_id) {
    return <div></div>
  }
  const [status, setStatus] = useState('')
  const updateStatus = async () => {
    // for testing
    // console.log("Message ID", params.message_id)
    // console.log('Sending payload:', JSON.stringify({ status }))
    try {
      const response = await fetch(API_URL + `/messages/${params.message_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',  // Add this line
        },
        body: JSON.stringify({ status }),
        credentials: 'include'
      })
      //console.log(response)

      if (!response.ok) {
        throw new Error('Failed to update status');
      }

      setStatus('')
      // added this due to page needing a refesh upon update
      window.location.reload()
    } catch (error) {
      console.error('Error updating status:', error);
    }
  }

  return (
    <div className='relative h-full'>
      <div className='h-full mx-auto max-w-3xl px-8'>
        <div className='h-full overflow-hidden bg-white ring-1 ring-gray-900/5 rounded-xl shadow'>
          <div className='h-full p-8 space-y-6'>
            <div className='space-y-1'>
              <h2 className='text-lg font-semibold leading-6 text-gray-900'>
                {message.subject}
              </h2>
              <p className='text-sm text-gray-500'>{message.from_email}</p>
            </div>
            <p>Status: {message.status}</p>
            <input 
                type="text" 
                value={status} 
                onChange={(e) => setStatus(e.target.value)} 
                placeholder="Enter new status" 
            />
            <button
              type='submit'
              className='flex justify-center rounded-md bg-pink-600 px-3 py-1.5 text-sm font-semibold leading-6 text-white shadow-sm hover:bg-pink-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pink-600'
              onClick={updateStatus}>Update Status
            </button>
            <p>{message.content}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
